from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from PIL import Image, ImageDraw


class Pose(str, Enum):
    STAND = "stand"
    TALK = "talk"
    WALK = "walk"
    THINK = "think"
    SHRUG = "shrug"
    FALL = "fall"
    CELEBRATE = "celebrate"
    PANIC = "panic"
    POINT = "point"
    SLUMP = "slump"


@dataclass
class StickStyle:
    stroke: str = "#111111"
    accent: str = "#E85D04"
    line_width: int = 6
    head_r: int = 42


def _xy(cx: float, cy: float, angle_deg: float, length: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return cx + math.cos(rad) * length, cy + math.sin(rad) * length


def draw_stick(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    pose: Pose | str,
    style: StickStyle,
    scale: float = 1.0,
    facing: int = 1,
    t: float = 0.0,
    label: str | None = None,
) -> None:
    """Draw a stick figure. (x, y) is the hip/center anchor."""
    pose = Pose(pose) if not isinstance(pose, Pose) else pose
    s = style
    w = max(2, int(s.line_width * scale))
    hr = int(s.head_r * scale)
    stroke = s.stroke
    bob = math.sin(t * math.pi * 2) * 4 * scale

    # Body proportions relative to hip
    neck_y = y - 110 * scale + bob
    head_y = neck_y - hr - 4
    hip_y = y + bob
    foot_y = y + 120 * scale

    # Pose-specific limb angles (degrees, 0 = right)
    left_arm = (200, 55)
    right_arm = (-20, 55)
    left_leg = (110, 70)
    right_leg = (70, 70)
    lean = 0.0

    if pose == Pose.TALK:
        right_arm = (-40 + 15 * math.sin(t * 10), 45)
        left_arm = (210, 50)
        bob = math.sin(t * math.pi * 4) * 3 * scale
        neck_y = y - 110 * scale + bob
        head_y = neck_y - hr - 4
        hip_y = y + bob
    elif pose == Pose.WALK:
        phase = t * math.pi * 2
        left_leg = (100 + 25 * math.sin(phase), 70)
        right_leg = (80 - 25 * math.sin(phase), 70)
        left_arm = (200 - 20 * math.sin(phase), 55)
        right_arm = (-20 + 20 * math.sin(phase), 55)
    elif pose == Pose.THINK:
        right_arm = (-80, 35)
        left_arm = (200, 45)
    elif pose == Pose.SHRUG:
        left_arm = (240, 40)
        right_arm = (-60, 40)
    elif pose == Pose.FALL:
        lean = 55 * facing
        left_arm = (250, 50)
        right_arm = (-70, 50)
        left_leg = (140, 65)
        right_leg = (40, 65)
    elif pose == Pose.CELEBRATE:
        left_arm = (250, 55)
        right_arm = (-70, 55)
        bob = abs(math.sin(t * math.pi * 4)) * 18 * scale
        neck_y = y - 110 * scale - bob
        head_y = neck_y - hr - 4
        hip_y = y - bob
    elif pose == Pose.PANIC:
        left_arm = (250 + 10 * math.sin(t * 20), 50)
        right_arm = (-70 - 10 * math.sin(t * 20), 50)
        bob = math.sin(t * 18) * 6 * scale
        neck_y = y - 110 * scale + bob
        head_y = neck_y - hr - 4
        hip_y = y + bob
    elif pose == Pose.POINT:
        right_arm = (0, 70)
        left_arm = (200, 45)
    elif pose == Pose.SLUMP:
        lean = 20 * facing
        left_arm = (190, 55)
        right_arm = (-10, 55)
        neck_y = y - 90 * scale
        head_y = neck_y - hr

    # Apply lean by shifting head/neck
    neck_x = x + lean * scale * 0.4 * facing
    head_x = neck_x

    # Head
    draw.ellipse(
        [head_x - hr, head_y - hr, head_x + hr, head_y + hr],
        outline=stroke,
        width=w,
    )
    # Accent hair tuft / CEO vibe
    draw.arc(
        [head_x - hr + 4, head_y - hr - 8, head_x + hr - 4, head_y],
        start=200,
        end=340,
        fill=s.accent,
        width=max(2, w - 1),
    )
    # Eyes
    eye_y = head_y - 6 * scale
    draw.ellipse(
        [head_x - 14 * scale, eye_y - 4 * scale, head_x - 6 * scale, eye_y + 4 * scale],
        fill=stroke,
    )
    draw.ellipse(
        [head_x + 6 * scale, eye_y - 4 * scale, head_x + 14 * scale, eye_y + 4 * scale],
        fill=stroke,
    )
    # Smile / panic mouth
    if pose in (Pose.PANIC, Pose.FALL):
        draw.ellipse(
            [head_x - 10 * scale, head_y + 10 * scale, head_x + 10 * scale, head_y + 26 * scale],
            outline=stroke,
            width=max(2, w - 2),
        )
    else:
        draw.arc(
            [head_x - 16 * scale, head_y + 4 * scale, head_x + 16 * scale, head_y + 28 * scale],
            start=20,
            end=160,
            fill=stroke,
            width=max(2, w - 2),
        )

    # Torso
    draw.line([(neck_x, neck_y), (x, hip_y)], fill=stroke, width=w)

    # Arms from neck
    for ang, length in (left_arm, right_arm):
        ang = ang if facing > 0 else (180 - ang)
        ex, ey = _xy(neck_x, neck_y + 10 * scale, ang, length * scale)
        draw.line([(neck_x, neck_y + 10 * scale), (ex, ey)], fill=stroke, width=w)

    # Legs from hip
    for ang, length in (left_leg, right_leg):
        ang = ang if facing > 0 else (180 - ang)
        ex, ey = _xy(x, hip_y, ang, length * scale)
        # Clamp near floor for standing poses
        if pose not in (Pose.FALL,):
            ey = min(ey, foot_y)
        draw.line([(x, hip_y), (ex, ey)], fill=stroke, width=w)

    # Tiny tie (CEO brand)
    tie_y = neck_y + 25 * scale
    draw.polygon(
        [
            (neck_x, neck_y + 8 * scale),
            (neck_x - 6 * scale, tie_y),
            (neck_x + 6 * scale, tie_y),
        ],
        fill=s.accent,
    )

    if label:
        from PIL import ImageFont

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((x - tw / 2, foot_y + 10), label, fill=stroke, font=font)


def draw_prop(draw: ImageDraw.ImageDraw, name: str, x: float, y: float, stroke: str, w: int = 5) -> None:
    n = name.lower()
    if "laptop" in n or "excel" in n or "computer" in n:
        draw.rectangle([x - 70, y - 50, x + 70, y + 20], outline=stroke, width=w)
        draw.rectangle([x - 60, y - 40, x + 60, y + 10], outline=stroke, width=max(2, w - 2))
        draw.line([(x - 40, y + 20), (x + 40, y + 20)], fill=stroke, width=w)
    elif "coffee" in n or "mug" in n:
        draw.arc([x - 30, y - 30, x + 20, y + 30], 270, 90, fill=stroke, width=w)
        draw.arc([x + 15, y - 10, x + 40, y + 20], 270, 90, fill=stroke, width=w)
    elif "printer" in n:
        draw.rectangle([x - 60, y - 40, x + 60, y + 40], outline=stroke, width=w)
        draw.rectangle([x - 40, y - 10, x + 40, y + 10], outline=stroke, width=max(2, w - 2))
    elif "duck" in n:
        draw.ellipse([x - 35, y - 20, x + 25, y + 25], outline=stroke, width=w)
        draw.ellipse([x + 10, y - 35, x + 40, y - 5], outline=stroke, width=w)
        draw.line([(x + 40, y - 20), (x + 55, y - 15)], fill=stroke, width=w)
    elif "board" in n or "chart" in n or "meeting" in n:
        draw.rectangle([x - 90, y - 70, x + 90, y + 50], outline=stroke, width=w)
        draw.line([(x - 60, y + 20), (x - 20, y - 30), (x + 20, y), (x + 60, y - 40)], fill=stroke, width=w)
    else:
        # Generic box prop
        draw.rectangle([x - 40, y - 40, x + 40, y + 40], outline=stroke, width=w)


def make_background(width: int, height: int, color: str) -> Image.Image:
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    # Soft floor line + doodle dots for atmosphere
    floor = int(height * 0.72)
    draw.line([(40, floor), (width - 40, floor)], fill="#DDD0B8", width=4)
    for i in range(12):
        px = 80 + i * (width // 12)
        py = 120 + (i * 37) % 200
        draw.ellipse([px, py, px + 6, py + 6], fill="#F0E6D0")
    return img


POSE_ALIASES = {p.value: p for p in Pose}


def normalize_pose(raw: str | None) -> Pose:
    if not raw:
        return Pose.STAND
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return POSE_ALIASES.get(key, Pose.STAND)


def available_poses() -> Sequence[str]:
    return [p.value for p in Pose]
