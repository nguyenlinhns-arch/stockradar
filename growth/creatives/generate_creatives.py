from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "source" / "creative_manifest.json"
OUTPUT = ROOT / "output"
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, minimum: int = 42) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > minimum:
        candidate = font(size, bold=True)
        widest = max(draw.textbbox((0, 0), line, font=candidate)[2] for line in text.splitlines())
        if widest <= max_width:
            return candidate
        size -= 2
    return font(minimum, bold=True)


def wrap_by_width(draw: ImageDraw.ImageDraw, text: str, chosen: ImageFont.FreeTypeFont, max_width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=chosen)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def draw_radar(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, accent: tuple[int, int, int]) -> None:
    cx, cy = center
    for ratio, alpha in ((1, 70), (.67, 95), (.34, 130)):
        r = int(radius * ratio)
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(*accent, alpha), width=max(2, radius // 70))
    draw.line((cx-radius, cy, cx+radius, cy), fill=(*accent, 35), width=2)
    draw.line((cx, cy-radius, cx, cy+radius), fill=(*accent, 35), width=2)
    angle = math.radians(-38)
    end = (cx + int(math.cos(angle)*radius), cy + int(math.sin(angle)*radius))
    draw.line((cx, cy, *end), fill=(*accent, 230), width=max(3, radius // 45))
    dot = (cx + int(radius*.64), cy - int(radius*.48))
    d = max(7, radius // 20)
    draw.ellipse((dot[0]-d, dot[1]-d, dot[0]+d, dot[1]+d), fill=(77, 229, 170, 255))


def render(item: dict[str, str], width: int, height: int, suffix: str) -> Path:
    scale = width / 1080
    accent = hex_color(item["accent"])
    image = Image.new("RGBA", (width, height), (7, 19, 29, 255))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            glow = max(0.0, 1 - math.hypot(x - width*.84, y - height*.08) / (width*.78))
            vignette = max(0.0, 1 - math.hypot(x - width*.12, y - height*.8) / (width*1.15))
            pixels[x, y] = (
                int(7 + accent[0]*.055*glow),
                int(19 + accent[1]*.08*glow + 6*vignette),
                int(29 + accent[2]*.075*glow + 9*vignette),
                255,
            )
    draw = ImageDraw.Draw(image, "RGBA")
    margin = int(74 * scale)
    for x in range(margin, width, int(74*scale)):
        for y in range(margin, height, int(74*scale)):
            draw.ellipse((x-2, y-2, x+2, y+2), fill=(255,255,255,18))

    radar_radius = int((230 if height < 1600 else 280) * scale)
    draw_radar(draw, (width-int(125*scale), int(170*scale)), radar_radius, accent)

    logo_font = font(int(42*scale), bold=True)
    draw.text((margin, margin), "STOCK", font=logo_font, fill=(245,248,247,255))
    stock_width = draw.textbbox((0,0), "STOCK", font=logo_font)[2]
    draw.text((margin+stock_width, margin), "RADAR", font=logo_font, fill=(*accent,255))

    kicker_y = int((310 if height < 1600 else 430) * scale)
    kicker_font = font(int(25*scale), bold=True)
    kicker_bbox = draw.textbbox((0,0), item["kicker"], font=kicker_font)
    kicker_w = kicker_bbox[2] + int(40*scale)
    draw.rounded_rectangle((margin, kicker_y, margin+kicker_w, kicker_y+int(52*scale)), radius=int(26*scale), fill=(*accent,255), outline=(*accent,255), width=2)
    draw.text((margin+int(20*scale), kicker_y+int(11*scale)), item["kicker"], font=kicker_font, fill=(7,19,29,255))

    title_y = kicker_y + int(92*scale)
    title_font = fit_text(draw, item["title"], width-2*margin, int((87 if height < 1600 else 94)*scale), int(48*scale))
    draw.multiline_text((margin, title_y), item["title"], font=title_font, fill=(247,250,249,255), spacing=int(15*scale))
    title_box = draw.multiline_textbbox((margin, title_y), item["title"], font=title_font, spacing=int(15*scale))

    subtitle_font = font(int((34 if height < 1600 else 38)*scale))
    subtitle = wrap_by_width(draw, item["subtitle"], subtitle_font, width-2*margin)
    subtitle_y = title_box[3] + int(48*scale)
    draw.multiline_text((margin, subtitle_y), subtitle, font=subtitle_font, fill=(188,205,210,255), spacing=int(14*scale))

    card_top = int(height - (335 if height < 1600 else 410)*scale)
    card_bottom = height - int(72*scale)
    draw.rounded_rectangle((margin, card_top, width-margin, card_bottom), radius=int(34*scale), fill=(14,39,52,235), outline=(255,255,255,32), width=2)
    state_font = font(int(26*scale), bold=True)
    states = ["WATCH", "NEAR TRIGGER", "READY"] if item["proposition"] != "risk" else ["READY", "INVALIDATED"]
    x = margin + int(30*scale)
    state_y = card_top + int(34*scale)
    for idx, state in enumerate(states):
        state_color = accent if idx == len(states)-1 else (117, 143, 153)
        label_w = draw.textbbox((0,0), state, font=state_font)[2] + int(34*scale)
        draw.rounded_rectangle((x, state_y, x+label_w, state_y+int(54*scale)), radius=int(27*scale), fill=(21,48,62,255), outline=(*state_color,255), width=2)
        draw.text((x+int(17*scale), state_y+int(12*scale)), state, font=state_font, fill=(*state_color,255))
        x += label_w + int(16*scale)
        if idx < len(states)-1:
            draw.text((x-int(8*scale), state_y+int(8*scale)), "→", font=font(int(31*scale),bold=True), fill=(105,129,139,255))
            x += int(26*scale)

    cta_y = card_top + int(126*scale)
    cta_font = font(int(31*scale), bold=True)
    cta_h = int(70*scale)
    cta_w = min(width-2*margin-int(60*scale), draw.textbbox((0,0), item["cta"], font=cta_font)[2] + int(62*scale))
    draw.rounded_rectangle((margin+int(30*scale), cta_y, margin+int(30*scale)+cta_w, cta_y+cta_h), radius=cta_h//2, fill=(*accent,255))
    draw.text((margin+int(61*scale), cta_y+int(17*scale)), item["cta"], font=cta_font, fill=(7,19,29,255))
    footer_font = font(int(22*scale))
    draw.text((margin+int(30*scale), card_bottom-int(52*scale)), "Sàng lọc setup · Không cam kết lợi nhuận", font=footer_font, fill=(139,158,166,255))

    output = OUTPUT / f"{item['id']}_{item['proposition']}_{suffix}.png"
    image.convert("RGB").save(output, quality=95, optimize=True)
    return output


def contact_sheet(files: list[Path]) -> Path:
    thumb_w, thumb_h = 324, 405
    canvas = Image.new("RGB", (thumb_w*3 + 80, thumb_h*2 + 110), (5,14,21))
    for index, path in enumerate(files):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = 20 + (index % 3) * (thumb_w + 20)
        y = 20 + (index // 3) * (thumb_h + 30)
        canvas.paste(image, (x, y))
    path = OUTPUT / "STOCKRADAR_CREATIVE_CONTACT_SHEET.png"
    canvas.save(path, quality=93)
    return path


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    feed_files: list[Path] = []
    for item in items:
        feed_files.append(render(item, 1080, 1350, "feed_4x5"))
        render(item, 1080, 1920, "reels_9x16")
    sheet = contact_sheet(feed_files)
    print(json.dumps({"creatives": len(items)*2, "contact_sheet": str(sheet)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
