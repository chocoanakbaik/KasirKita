"""Generate deterministic KasirKita brand assets for the desktop UI and Windows build."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
ICONS = ROOT / "assets" / "icons"
BRAND.mkdir(parents=True, exist_ok=True)
ICONS.mkdir(parents=True, exist_ok=True)

BG = (15, 118, 110, 255)
BG_DARK = (22, 78, 99, 255)
WHITE = (248, 250, 252, 255)
INK = (23, 32, 51, 255)
GOLD = (245, 158, 11, 255)


def draw_mark(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = round(size * 0.035)
    radius = round(size * 0.22)
    draw.rounded_rectangle((margin, margin, size - margin, size - margin),
                           radius=radius, fill=BG)
    # Shopping bag body
    left, top = round(size * .29), round(size * .37)
    right, bottom = round(size * .71), round(size * .76)
    draw.rounded_rectangle((left, top, right, bottom),
                           radius=round(size * .055), fill=WHITE)
    # Handle
    draw.arc((round(size * .39), round(size * .20),
              round(size * .61), round(size * .48)),
             180, 360, fill=WHITE, width=max(2, round(size * .045)))
    # Check mark
    points = [(round(size * .39), round(size * .55)),
              (round(size * .47), round(size * .63)),
              (round(size * .63), round(size * .47))]
    draw.line(points, fill=BG_DARK, width=max(2, round(size * .055)),
              joint="curve")
    # Gold corner dot
    r = round(size * .095)
    cx, cy = round(size * .73), round(size * .73)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=GOLD)
    return image


def main() -> None:
    mark = draw_mark(512)
    mark.save(ICONS / "kasirkita-mark.png", optimize=True)
    mark.save(ICONS / "kasirkita.ico", format="ICO",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                     (64, 64), (128, 128), (256, 256)])

    # Horizontal wordmark used by the app header and splash screen.
    canvas = Image.new("RGBA", (660, 160), (0, 0, 0, 0))
    small_mark = mark.resize((136, 136), Image.Resampling.LANCZOS)
    canvas.alpha_composite(small_mark, (0, 12))
    draw = ImageDraw.Draw(canvas)
    font = None
    for candidate in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(candidate, 54)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((158, 30), "KasirKita", font=font, fill=INK)
    tagline_font = ImageFont.truetype(font.path, 19) if getattr(font, "path", None) else ImageFont.load_default()
    draw.text((161, 94), "KASIR DESKTOP  •  OFFLINE-FIRST",
              font=tagline_font, fill=BG_DARK)
    canvas.save(BRAND / "kasirkita-logo.png", optimize=True)


if __name__ == "__main__":
    main()
