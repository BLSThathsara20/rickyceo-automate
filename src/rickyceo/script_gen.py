from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from .config import load_config
from .stick import available_poses


SCRIPT_SCHEMA_HINT = """
Return ONLY valid JSON (no markdown) with this shape:
{
  "title": "catchy YouTube Shorts title under 70 chars",
  "description": "2-3 sentence description ending with #Shorts #RickyCEO",
  "tags": ["tag1", "tag2"],
  "hook": "first line hook",
  "narration": "full spoken narration 80-140 words, funny, first or third person about Ricky the CEO stickman",
  "scenes": [
    {
      "visual": "short visual description",
      "pose": "one of: stand|talk|walk|think|shrug|fall|celebrate|panic|point|slump",
      "prop": "optional prop keyword or empty string",
      "other_pose": "optional second character pose or empty",
      "line": "caption line for this beat",
      "duration_hint": 3.0
    }
  ]
}
Use 5 to 8 scenes. Keep it clean workplace comedy, slapstick, no hate speech.
"""


@dataclass
class Scene:
    visual: str
    pose: str
    line: str
    duration_hint: float = 3.0
    prop: str = ""
    other_pose: str = ""


@dataclass
class VideoScript:
    title: str
    description: str
    tags: list[str]
    hook: str
    narration: str
    scenes: list[Scene] = field(default_factory=list)
    topic: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "hook": self.hook,
            "narration": self.narration,
            "topic": self.topic,
            "scenes": [
                {
                    "visual": s.visual,
                    "pose": s.pose,
                    "prop": s.prop,
                    "other_pose": s.other_pose,
                    "line": s.line,
                    "duration_hint": s.duration_hint,
                }
                for s in self.scenes
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], topic: str = "") -> VideoScript:
        scenes = []
        for raw in data.get("scenes") or []:
            scenes.append(
                Scene(
                    visual=str(raw.get("visual") or ""),
                    pose=str(raw.get("pose") or "stand"),
                    prop=str(raw.get("prop") or ""),
                    other_pose=str(raw.get("other_pose") or ""),
                    line=str(raw.get("line") or ""),
                    duration_hint=float(raw.get("duration_hint") or 3.0),
                )
            )
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return cls(
            title=str(data.get("title") or "RickyCEO Short"),
            description=str(data.get("description") or ""),
            tags=[str(t) for t in tags],
            hook=str(data.get("hook") or ""),
            narration=str(data.get("narration") or ""),
            scenes=scenes,
            topic=topic or str(data.get("topic") or ""),
        )


def pick_auto_idea(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_config()
    ideas = cfg.get("ideas") or ["CEO fails at email"]
    return random.choice(ideas)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _validate(script: VideoScript) -> VideoScript:
    if not script.narration.strip():
        raise ValueError("Script missing narration")
    if len(script.scenes) < 3:
        raise ValueError("Need at least 3 scenes")
    poses = set(available_poses())
    for scene in script.scenes:
        if scene.pose.lower() not in poses:
            scene.pose = "talk"
        if scene.other_pose and scene.other_pose.lower() not in poses:
            scene.other_pose = "stand"
        scene.duration_hint = max(1.5, min(8.0, float(scene.duration_hint)))
    if "Shorts" not in script.description:
        script.description = (script.description.strip() + "\n\n#Shorts #RickyCEO").strip()
    return script


def _fallback_script(topic: str) -> VideoScript:
    return VideoScript(
        title=f"RickyCEO: {topic[:50]}",
        description=f"Ricky the CEO stickman vs {topic}. #Shorts #RickyCEO #comedy",
        tags=["Shorts", "funny", "CEO", "RickyCEO", "stickman"],
        hook=f"When {topic.lower()}...",
        narration=(
            f"Ricky the CEO thought {topic.lower()} would be easy. "
            "He walked into the office like a legend, opened his laptop, and immediately broke Excel. "
            "The coffee machine got promoted. The printer filed a complaint. "
            "Ricky panicked, shrugged, then celebrated anyway because confidence is a business strategy. "
            "Moral of the story: fake it till the board meeting ends."
        ),
        topic=topic,
        scenes=[
            Scene("Ricky intro", "stand", "Meet Ricky the CEO", 3, "", ""),
            Scene("Confident walk", "walk", "He has a vision", 3, "", ""),
            Scene("Laptop fail", "talk", "Excel has entered the chat", 4, "laptop", "think"),
            Scene("Panic", "panic", "Synergy is gone", 3, "coffee", "shrug"),
            Scene("Printer wins", "fall", "Printer: 1  CEO: 0", 3, "printer", "celebrate"),
            Scene("Celebrate anyway", "celebrate", "Still calling it a win", 3, "", "shrug"),
        ],
    )


def generate_script(topic: str, cfg: dict[str, Any] | None = None, use_fallback: bool = False) -> VideoScript:
    cfg = cfg or load_config()
    if use_fallback:
        return _validate(_fallback_script(topic))

    ollama = cfg.get("ollama") or {}
    host = str(ollama.get("host") or "http://127.0.0.1:11434").rstrip("/")
    model = str(ollama.get("model") or "llama3.2")
    temperature = float(ollama.get("temperature") or 0.9)

    prompt = (
        f"Write a funny YouTube Shorts script about stickman CEO Ricky.\n"
        f"Topic: {topic}\n"
        f"Allowed poses: {', '.join(available_poses())}\n"
        f"{SCRIPT_SCHEMA_HINT}"
    )

    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = requests.post(
                f"{host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
                timeout=180,
            )
            if resp.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{model}' not found. Run: ollama pull {model}"
                )
            resp.raise_for_status()
            raw_text = resp.json().get("response") or ""
            data = _extract_json(raw_text)
            return _validate(VideoScript.from_dict(data, topic=topic))
        except Exception as exc:  # noqa: BLE001 — retry then fallback
            last_err = exc

    # If Ollama is down, still produce a usable video
    print(f"[script_gen] Ollama failed ({last_err}); using local fallback script.")
    return _validate(_fallback_script(topic))


def ollama_available(cfg: dict[str, Any] | None = None) -> bool:
    cfg = cfg or load_config()
    host = str((cfg.get("ollama") or {}).get("host") or "http://127.0.0.1:11434").rstrip("/")
    try:
        r = requests.get(f"{host}/api/tags", timeout=3)
        return r.ok
    except requests.RequestException:
        return False


def save_script(script: VideoScript, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(script.to_dict(), indent=2), encoding="utf-8")


def load_script(path: Path) -> VideoScript:
    data = json.loads(path.read_text(encoding="utf-8"))
    return VideoScript.from_dict(data)
