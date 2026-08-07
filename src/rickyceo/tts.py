from __future__ import annotations

import asyncio
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from .config import load_config, project_root


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate) if rate else 0.0


def _piper_ready(cfg: dict[str, Any]) -> bool:
    tts = cfg.get("tts") or {}
    binary = str(tts.get("piper_binary") or "piper")
    voice = project_root() / str(tts.get("piper_voice") or "assets/voices/en_US-lessac-medium.onnx")
    return shutil.which(binary) is not None and voice.exists()


def synthesize_piper(text: str, out_wav: Path, cfg: dict[str, Any]) -> Path:
    tts = cfg.get("tts") or {}
    binary = str(tts.get("piper_binary") or "piper")
    voice = project_root() / str(tts.get("piper_voice") or "assets/voices/en_US-lessac-medium.onnx")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [binary, "--model", str(voice), "--output_file", str(out_wav)]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return out_wav


async def _edge_save(text: str, out_wav: Path, voice: str, rate: str) -> None:
    import edge_tts

    # edge-tts writes mp3 by default; we ask for wav via communicate + ffmpeg if needed
    tmp_mp3 = out_wav.with_suffix(".mp3")
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(tmp_mp3))
    # Convert to wav for consistent duration probing
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(tmp_mp3),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "22050",
            "-ac",
            "1",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )
    tmp_mp3.unlink(missing_ok=True)


def synthesize_edge(text: str, out_wav: Path, cfg: dict[str, Any]) -> Path:
    tts = cfg.get("tts") or {}
    voice = str(tts.get("edge_voice") or "en-US-GuyNeural")
    speaking_rate = float(tts.get("speaking_rate") or 1.0)
    # edge-tts rate like "+5%"
    pct = int(round((speaking_rate - 1.0) * 100))
    rate = f"{pct:+d}%"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_edge_save(text, out_wav, voice, rate))
    return out_wav


def synthesize_speech(text: str, out_wav: Path, cfg: dict[str, Any] | None = None) -> Path:
    """Synthesize narration. Prefers Piper when available; else edge-tts."""
    cfg = cfg or load_config()
    engine = str((cfg.get("tts") or {}).get("engine") or "auto").lower()
    text = " ".join(text.split())
    if not text:
        raise ValueError("Empty narration for TTS")

    if engine == "piper" or (engine == "auto" and _piper_ready(cfg)):
        print("[tts] Using Piper")
        return synthesize_piper(text, out_wav, cfg)

    if engine in ("edge", "edge-tts", "auto"):
        print("[tts] Using edge-tts (Piper not configured)")
        return synthesize_edge(text, out_wav, cfg)

    raise RuntimeError(
        "No TTS engine available. Install Piper + voice model, or keep edge-tts in requirements."
    )
