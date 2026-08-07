from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ensure_dirs, load_config, project_root
from .render import render_video
from .script_gen import generate_script, load_script, pick_auto_idea, save_script
from .tts import synthesize_speech
from .youtube_upload import upload_video


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (slug[:50] or "short")


def new_run_dir(topic: str) -> Path:
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = project_root() / "output" / f"{stamp}-{_slugify(topic)}"
    path.mkdir(parents=True, exist_ok=True)
    latest = project_root() / "output" / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    try:
        latest.symlink_to(path, target_is_directory=True)
    except OSError:
        # Fallback marker file on platforms that dislike symlinks
        latest.write_text(str(path), encoding="utf-8")
    return path


def resolve_run_dir(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = project_root() / p
    if p.name == "latest" and p.is_file():
        p = Path(p.read_text(encoding="utf-8").strip())
    return p


def generate_package(
    topic: str | None = None,
    *,
    auto_idea: bool = False,
    script_file: Path | None = None,
    use_fallback_script: bool = False,
    cfg: dict[str, Any] | None = None,
) -> Path:
    cfg = cfg or load_config()
    if script_file:
        script = load_script(Path(script_file))
        topic = script.topic or topic or "custom"
    else:
        if auto_idea or not topic:
            topic = pick_auto_idea(cfg)
        assert topic
        script = generate_script(topic, cfg, use_fallback=use_fallback_script)

    out_dir = new_run_dir(topic or "short")
    save_script(script, out_dir / "script.json")

    audio = synthesize_speech(script.narration, out_dir / "narration.wav", cfg)
    video = render_video(script, audio, out_dir, cfg)

    meta = {
        **script.to_dict(),
        "video": str(video),
        "audio": str(audio),
        "output_dir": str(out_dir),
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[generate] Done → {out_dir}")
    print(f"[generate] Video → {video}")
    return out_dir


def upload_package(run_dir: Path, privacy: str | None = None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    run_dir = resolve_run_dir(run_dir)
    meta_path = run_dir / "metadata.json"
    script_path = run_dir / "script.json"
    video_path = run_dir / "final.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"No final.mp4 in {run_dir}")

    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    elif script_path.exists():
        meta = json.loads(script_path.read_text(encoding="utf-8"))
    else:
        raise FileNotFoundError("Need metadata.json or script.json")

    privacy = privacy or str((cfg.get("channel") or {}).get("default_privacy") or "private")
    result = upload_video(
        video_path,
        title=str(meta.get("title") or "RickyCEO Short"),
        description=str(meta.get("description") or "#Shorts #RickyCEO"),
        tags=list(meta.get("tags") or []),
        privacy=privacy,
        cfg=cfg,
    )
    (run_dir / "upload.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_all(
    topic: str | None = None,
    *,
    auto_idea: bool = False,
    privacy: str = "private",
    use_fallback_script: bool = False,
    skip_upload: bool = False,
    cfg: dict[str, Any] | None = None,
) -> Path:
    out_dir = generate_package(
        topic,
        auto_idea=auto_idea,
        use_fallback_script=use_fallback_script,
        cfg=cfg,
    )
    if not skip_upload:
        upload_package(out_dir, privacy=privacy, cfg=cfg)
    return out_dir
