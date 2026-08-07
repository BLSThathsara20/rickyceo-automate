from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .captions import draw_caption, draw_title_card
from .config import load_config
from .script_gen import Scene, VideoScript
from .stick import StickStyle, draw_prop, draw_stick, make_background, normalize_pose
from .tts import wav_duration_seconds


def _allocate_scene_durations(scenes: list[Scene], total_audio: float) -> list[float]:
    hints = [max(1.5, s.duration_hint) for s in scenes]
    hint_sum = sum(hints) or 1.0
    # Reserve ~1.2s for title card at start (visual only; audio starts with narration)
    usable = max(total_audio, 8.0)
    return [usable * (h / hint_sum) for h in hints]


def render_frames(
    script: VideoScript,
    out_dir: Path,
    audio_wav: Path,
    cfg: dict[str, Any] | None = None,
) -> tuple[Path, list[float]]:
    cfg = cfg or load_config()
    video = cfg.get("video") or {}
    character = cfg.get("character") or {}
    width = int(video.get("width") or 1080)
    height = int(video.get("height") or 1920)
    fps = int(video.get("fps") or 12)
    bg = str(video.get("background") or "#FFF8E7")
    caption_color = str(video.get("caption_color") or "#111111")
    caption_outline = str(video.get("caption_outline") or "#FFFFFF")

    style = StickStyle(
        stroke=str(character.get("stroke") or "#111111"),
        accent=str(character.get("accent") or "#E85D04"),
        line_width=int(character.get("line_width") or 6),
    )

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    audio_dur = wav_duration_seconds(audio_wav)
    durations = _allocate_scene_durations(script.scenes, audio_dur)

    frame_idx = 0
    # Title card ~1 second
    title_frames = max(1, int(fps * 1.0))
    for i in range(title_frames):
        img = make_background(width, height, bg)
        draw_title_card(img, script.title, brand=str((cfg.get("channel") or {}).get("name") or "RickyCEO"))
        img.save(frames_dir / f"frame_{frame_idx:05d}.png")
        frame_idx += 1

    floor_y = int(height * 0.62)
    ricky_x = int(width * 0.38)
    other_x = int(width * 0.68)

    for scene, dur in zip(script.scenes, durations, strict=True):
        n_frames = max(1, int(round(dur * fps)))
        pose = normalize_pose(scene.pose)
        other_pose = normalize_pose(scene.other_pose) if scene.other_pose else None
        for i in range(n_frames):
            t = i / max(1, n_frames - 1)
            img = make_background(width, height, bg)
            draw = ImageDraw.Draw(img)

            # Prop
            if scene.prop:
                draw_prop(draw, scene.prop, width * 0.5, floor_y - 40, style.stroke, style.line_width)

            draw_stick(
                draw,
                ricky_x,
                floor_y,
                pose,
                style,
                scale=1.15,
                facing=1,
                t=t,
                label="Ricky",
            )
            if other_pose:
                draw_stick(
                    draw,
                    other_x,
                    floor_y,
                    other_pose,
                    StickStyle(
                        stroke="#333333",
                        accent="#4A6FA5",
                        line_width=style.line_width,
                    ),
                    scale=1.0,
                    facing=-1,
                    t=t,
                    label="Coworker",
                )

            caption = scene.line or scene.visual
            draw_caption(
                img,
                caption,
                fill=caption_color,
                outline=caption_outline,
            )
            img.save(frames_dir / f"frame_{frame_idx:05d}.png")
            frame_idx += 1

    timing_path = out_dir / "timing.json"
    timing_path.write_text(
        json.dumps({"fps": fps, "audio_seconds": audio_dur, "scene_seconds": durations}, indent=2),
        encoding="utf-8",
    )
    return frames_dir, durations


def assemble_video(frames_dir: Path, audio_wav: Path, out_mp4: Path, fps: int = 12) -> Path:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames_dir / "frame_%05d.png")
    # Encode video from frames, then mux audio (shortest = cut video to audio if needed)
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
        "-i",
        str(audio_wav),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4


def render_video(
    script: VideoScript,
    audio_wav: Path,
    out_dir: Path,
    cfg: dict[str, Any] | None = None,
) -> Path:
    cfg = cfg or load_config()
    fps = int((cfg.get("video") or {}).get("fps") or 12)
    frames_dir, _ = render_frames(script, out_dir, audio_wav, cfg)
    out_mp4 = out_dir / "final.mp4"
    return assemble_video(frames_dir, audio_wav, out_mp4, fps=fps)
