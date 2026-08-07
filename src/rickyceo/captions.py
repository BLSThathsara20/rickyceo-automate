from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def get_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_caption(
    img: Image.Image,
    text: str,
    *,
    fill: str = "#111111",
    outline: str = "#FFFFFF",
    y_ratio: float = 0.78,
) -> None:
    if not text.strip():
        return
    draw = ImageDraw.Draw(img)
    font = get_font(size=max(36, img.width // 18))
    max_w = int(img.width * 0.86)
    lines = wrap_text(text.strip(), font, max_w, draw)
    line_h = font.size + 10
    total_h = line_h * len(lines)
    y = int(img.height * y_ratio) - total_h // 2
    for line in lines:
        tw = draw.textlength(line, font=font)
        x = (img.width - tw) / 2
        # Outline
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            draw.text((x + dx, y + dy), line, font=font, fill=outline)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h


def draw_title_card(img: Image.Image, title: str, brand: str = "RickyCEO") -> None:
    draw = ImageDraw.Draw(img)
    brand_font = get_font(size=max(48, img.width // 14))
    title_font = get_font(size=max(40, img.width // 16))
    # Brand
    bw = draw.textlength(brand, font=brand_font)
    bx = (img.width - bw) / 2
    by = img.height * 0.12
    for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((bx + dx, by + dy), brand, font=brand_font, fill="#FFFFFF")
    draw.text((bx, by), brand, font=brand_font, fill="#E85D04")
    # Title
    lines = wrap_text(title, title_font, int(img.width * 0.85), draw)
    y = img.height * 0.22
    for line in lines[:3]:
        tw = draw.textlength(line, font=title_font)
        x = (img.width - tw) / 2
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, font=title_font, fill="#FFFFFF")
        draw.text((x, y), line, font=title_font, fill="#111111")
        y += title_font.size + 12
