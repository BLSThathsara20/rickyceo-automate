# RickyCEO — YouTube Shorts automation

Fully automatic **local** pipeline for [@RickyCEO](https://www.youtube.com/@RickyCEO):

**idea → funny script (Ollama) → voice (Piper or edge-tts) → stick-figure Short → YouTube upload**

Runs on your Mac with local tools and the official YouTube Data API.

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) (`brew install ffmpeg`)
- [Ollama](https://ollama.com) + a model (`ollama pull llama3.2`) — optional; `--fallback-script` works offline
- Google account that owns the channel (one-time OAuth)

## Setup

```bash
cd automate-youtube
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Optional but recommended for better scripts
ollama pull llama3.2

# YouTube upload
# 1. Google Cloud Console → enable YouTube Data API v3
# 2. Create OAuth client (Desktop app)
# 3. Download JSON → credentials/client_secret.json
mkdir -p credentials
```

Check your machine:

```bash
python -m rickyceo doctor
```

## Usage

```bash
# Generate only (safe) — uses Ollama if available, else local fallback
python -m rickyceo generate --topic "CEO discovers Excel"

# Or pick a random idea from config.yaml
python -m rickyceo generate --auto-idea

# Force offline template script (no Ollama)
python -m rickyceo generate --topic "Printer war" --fallback-script

# Upload latest run as PRIVATE (recommended first)
python -m rickyceo upload output/latest --privacy private

# Full auto (still defaults to private)
python -m rickyceo run --auto-idea --privacy private

# Go public when you are happy with quality
python -m rickyceo run --topic "Standup lasts 3 hours" --privacy public
```

Outputs land in `output/<timestamp>-<slug>/`:

- `script.json` / `metadata.json`
- `narration.wav`
- `frames/`
- `final.mp4`

`output/latest` points at the most recent run.

## TTS notes

- **Piper** (fully offline): install the `piper` binary and put an ONNX voice in `assets/voices/` (see `assets/voices/README.md`).
- If Piper is missing, the pipeline uses **edge-tts** (Microsoft voices; needs network, no API key).

## Daily automation (optional)

After `run` works once:

```bash
# Example cron: 1 private Short per day at 9:00
0 9 * * * cd /path/to/automate-youtube && .venv/bin/python -m rickyceo run --auto-idea --privacy private
```

Review privately, then re-upload or change privacy in YouTube Studio until you trust quality.

## Limits

- YouTube API default quota ≈ **6 uploads/day** (you can request a higher quota if needed).
- Stick figures are code-drawn on purpose (brandable, no GPU required).
- Do not spam; low-quality floods can hurt the channel.

## Project layout

```
src/rickyceo/     # CLI + pipeline
config.yaml       # channel, video, ideas, voices
credentials/      # OAuth secrets (gitignored)
output/           # generated Shorts (gitignored)
```
