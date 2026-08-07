from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ensure_dirs, load_config, project_root
from .pipeline import generate_package, run_all, upload_package
from .script_gen import ollama_available


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rickyceo",
        description="Local $0 stick-figure Shorts pipeline for @RickyCEO",
    )
    sub = p.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate script + voice + video (no upload)")
    gen.add_argument("--topic", type=str, default=None, help="Comedy topic")
    gen.add_argument("--auto-idea", action="store_true", help="Pick a random idea from config")
    gen.add_argument("--script-file", type=Path, default=None, help="Use an existing script JSON")
    gen.add_argument(
        "--fallback-script",
        action="store_true",
        help="Skip Ollama and use the built-in template script",
    )

    up = sub.add_parser("upload", help="Upload an existing output folder")
    up.add_argument("run_dir", type=str, help="Path like output/latest or output/<run>")
    up.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default=None,
        help="Privacy status (default: config / private)",
    )

    run = sub.add_parser("run", help="Generate and upload")
    run.add_argument("--topic", type=str, default=None)
    run.add_argument("--auto-idea", action="store_true")
    run.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="Default private for safe dry-run",
    )
    run.add_argument("--fallback-script", action="store_true")
    run.add_argument("--skip-upload", action="store_true", help="Same as generate")

    sub.add_parser("doctor", help="Check local dependencies")
    return p


def cmd_doctor() -> int:
    import shutil

    ensure_dirs()
    cfg = load_config()
    hard_fail = False

    def check(name: str, good: bool, hint: str = "", *, required: bool = False) -> None:
        nonlocal hard_fail
        if good:
            status = "OK"
        elif required:
            status = "MISSING"
            hard_fail = True
        else:
            status = "OPTIONAL"
        print(f"  [{status}] {name}" + (f" — {hint}" if hint and not good else ""))

    print("RickyCEO doctor")
    check("ffmpeg", shutil.which("ffmpeg") is not None, "brew install ffmpeg", required=True)
    check(
        "ollama server",
        ollama_available(cfg),
        "Install Ollama and run: ollama pull llama3.2 (or use --fallback-script)",
        required=False,
    )
    piper = shutil.which(str((cfg.get("tts") or {}).get("piper_binary") or "piper"))
    voice = Path(str((cfg.get("tts") or {}).get("piper_voice") or "assets/voices/en_US-lessac-medium.onnx"))
    voice_path = voice if voice.is_absolute() else project_root() / voice
    check(
        "piper TTS",
        piper is not None and voice_path.exists(),
        "Optional; edge-tts is used automatically if Piper is missing",
        required=False,
    )
    secrets = project_root() / "credentials" / "client_secret.json"
    check(
        "YouTube OAuth client_secret.json",
        secrets.exists(),
        "Needed only for upload: place OAuth Desktop JSON at credentials/client_secret.json",
        required=False,
    )
    try:
        import edge_tts  # noqa: F401
        import PIL  # noqa: F401
        import yaml  # noqa: F401

        check("python deps", True, required=True)
    except ImportError as exc:
        check("python deps", False, f"pip install -e . ({exc})", required=True)

    return 1 if hard_fail else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ensure_dirs()
    cfg = load_config()

    if args.command == "doctor":
        return cmd_doctor()

    if args.command == "generate":
        generate_package(
            args.topic,
            auto_idea=args.auto_idea,
            script_file=args.script_file,
            use_fallback_script=args.fallback_script,
            cfg=cfg,
        )
        return 0

    if args.command == "upload":
        upload_package(args.run_dir, privacy=args.privacy, cfg=cfg)
        return 0

    if args.command == "run":
        run_all(
            args.topic,
            auto_idea=args.auto_idea,
            privacy=args.privacy,
            use_fallback_script=args.fallback_script,
            skip_upload=args.skip_upload,
            cfg=cfg,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
