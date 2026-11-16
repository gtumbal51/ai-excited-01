"""ai-excited-01 entry: "Jump the Moon".

A program that draws one image and writes it to /output/entry.png.

The image: a giant koi leaps in a great arc over a full moon, a ribbon of spray
trailing behind it, over a night sea. Drawn from scratch with the Python
standard library only (no image libraries exist in the grader sandbox): a small
span-based vector renderer on top of a raw RGB framebuffer, then a hand-rolled
PNG encoder (zlib + per-row adaptive filtering).

Deterministic: every number comes from fixed constants and a fixed-seed
generator, so two runs write byte-identical files.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- framebuffer

fb = [bytearray(W * 3) for _ in range(H)]


def clamp_byte(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def set_span(y, x0, x1, rgb):
    """Fill pixels [x0, x1) on row y with an opaque colour."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x1 <= x0:
        return
    r, g, b = rgb
    fb[y][x0 * 3:x1 * 3] = bytes((r, g, b)) * (x1 - x0)


def blend_span(y, x0, x1, rgb, alpha):
    """Blend pixels [x0, x1) on row y toward rgb by alpha (0..1)."""
    if y < 0 or y >= H or alpha <= 0.0:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x1 <= x0:
        return
    row = fb[y]
    r, g, b = rgb
    ia = 1.0 - alpha
    for x in range(x0, x1):
        i = x * 3
        row[i] = clamp_byte(row[i] * ia + r * alpha)
        row[i + 1] = clamp_byte(row[i + 1] * ia + g * alpha)
        row[i + 2] = clamp_byte(row[i + 2] * ia + b * alpha)


def disc(cx, cy, r, rgb, alpha=1.0):
    """Filled circle, opaque or blended."""
    if r <= 0:
        return
    r2 = r * r
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    for y in range(y0, y1 + 1):
        dy = y - cy
        dx = math.sqrt(max(0.0, r2 - dy * dy))
        x0 = int(cx - dx)
        x1 = int(cx + dx) + 1
        if alpha >= 1.0:
            set_span(y, x0, x1, rgb)
        else:
            blend_span(y, x0, x1, rgb, alpha)


def ellipse(cx, cy, rx, ry, rgb, alpha=1.0):
    """Filled axis-aligned ellipse, opaque or blended."""
    if rx <= 0 or ry <= 0:
        return
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        x0 = int(cx - dx)
        x1 = int(cx + dx) + 1
        if alpha >= 1.0:
            set_span(y, x0, x1, rgb)
        else:
            blend_span(y, x0, x1, rgb, alpha)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c1, c2, t):
    return (clamp_byte(lerp(c1[0], c2[0], t)),
            clamp_byte(lerp(c1[1], c2[1], t)),
            clamp_byte(lerp(c1[2], c2[2], t)))


# Fixed-seed deterministic pseudo-random generator (same sequence every run).
_seed = [123456789]


def rnd():
    _seed[0] = (_seed[0] * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed[0] / 0x7FFFFFFF


# ---------------------------------------------------------------- curves


def cubic(p0, p1, p2, p3, t):
    mt = 1.0 - t
    return (mt * mt * mt * p0[0] + 3 * mt * mt * t * p1[0]
            + 3 * mt * t * t * p2[0] + t * t * t * p3[0],
            mt * mt * mt * p0[1] + 3 * mt * mt * t * p1[1]
            + 3 * mt * t * t * p2[1] + t * t * t * p3[1])


def cubic_tangent(p0, p1, p2, p3, t):
    mt = 1.0 - t
    dx = 3 * mt * mt * (p1[0] - p0[0]) + 6 * mt * t * (p2[0] - p1[0]) \
        + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * mt * mt * (p1[1] - p0[1]) + 6 * mt * t * (p2[1] - p1[1]) \
        + 3 * t * t * (p3[1] - p2[1])
    n = math.hypot(dx, dy) or 1.0
    return (dx / n, dy / n)


def down_normal(tangent):
    """Unit normal pointing toward the bottom of the screen (+y)."""
    nx, ny = -tangent[1], tangent[0]
    if ny < 0:
        nx, ny = -nx, -ny
    return (nx, ny)


def trace_discs(p0, p1, p2, p3, n, radius_fn, rgb, alpha=1.0):
    """Draw a tapered band of discs along a cubic curve."""
    for i in range(n + 1):
        t = i / n
        x, y = cubic(p0, p1, p2, p3, t)
        disc(x, y, radius_fn(t), rgb, alpha)


# ---------------------------------------------------------------- sky & moon

SKY_TOP = (7, 10, 38)
SKY_BOTTOM = (56, 26, 90)
MOON_C = (640.0, 360.0)
MOON_R = 215.0
MOON_COL = (247, 243, 227)
CRATER_COL = (226, 215, 184)


def draw_sky():
    for y in range(H):
        t = (y / (H - 1)) ** 1.1
        set_span(y, 0, W, lerp_rgb(SKY_TOP, SKY_BOTTOM, t))


def draw_stars():
    for _ in range(150):
        x = rnd() * W
        y = rnd() * 940
        if math.hypot(x - MOON_C[0], y - MOON_C[1]) < MOON_R + 18:
            continue
        pick = rnd()
        if pick < 0.65:
            col, r, a = (255, 255, 255), 1.2, 0.55 + rnd() * 0.45
        elif pick < 0.85:
            col, r, a = (255, 233, 176), 1.6, 0.6 + rnd() * 0.4
        else:
            col, r, a = (207, 228, 255), 2.0, 0.6 + rnd() * 0.4
        disc(x, y, r, col, a)
        if r >= 2.0 and rnd() < 0.4:
            # four-point sparkle
            set_span(int(y), int(x - 5), int(x + 6), col)
            for yy in range(int(y - 5), int(y + 6)):
                if 0 <= yy < H:
                    set_span(yy, int(x), int(x + 1), col)


def draw_moon():
    # soft violet halo, brightest near the disc
    for radius, alpha in ((380, 0.04), (340, 0.05), (300, 0.07),
                          (260, 0.10), (235, 0.14)):
        disc(MOON_C[0], MOON_C[1], radius, (122, 90, 176), alpha)
    disc(MOON_C[0], MOON_C[1], MOON_R, MOON_COL)
    craters = ((-80, -60, 26), (40, -90, 18), (90, 30, 22), (-20, 70, 15),
               (120, -40, 12), (-130, 20, 16), (60, 110, 14), (-60, -120, 10))
    for dx, dy, r in craters:
        disc(MOON_C[0] + dx, MOON_C[1] + dy, r, CRATER_COL, 0.5)


# ---------------------------------------------------------------- sea

def draw_sea():
    for y in range(952, H):
        t = (y - 952) / (H - 1 - 952)
        set_span(y, 0, W, lerp_rgb((13, 27, 74), (8, 16, 48), t))
    # ripple rings
    for cx, cy, rx, ry in ((300, 968, 180, 7), (650, 982, 240, 8),
                           (480, 996, 300, 9)):
        ellipse(cx, cy, rx, ry, (150, 200, 255), 0.30)
        ellipse(cx, cy, rx - 3, ry - 2, lerp_rgb((13, 27, 74), (8, 16, 48),
                                                 (cy - 952) / 72.0), 1.0)


# ---------------------------------------------------------------- the koi

KOI_P0 = (95.0, 815.0)
KOI_P1 = (300.0, 470.0)
KOI_P2 = (560.0, 235.0)
KOI_P3 = (855.0, 425.0)
KOI_R = 52.0
KOI_BACK = (232, 84, 47)
KOI_BELLY = (255, 242, 216)
KOI_DARK = (194, 58, 30)
KOI_FIN = (255, 140, 66)


def koi_profile(t):
    keys = ((0.0, 0.14), (0.15, 0.72), (0.5, 1.0), (0.85, 0.85), (1.0, 0.72))
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def draw_koi():
    # tail fins first, so the body overlaps their roots
    trace_discs(KOI_P0, (30.0, 745.0), (12.0, 700.0), (8.0, 665.0), 26,
                lambda t: 18.0 * (1.0 - t) + 3.0, KOI_FIN, 0.5)
    trace_discs(KOI_P0, (25.0, 810.0), (10.0, 822.0), (2.0, 830.0), 22,
                lambda t: 13.0 * (1.0 - t) + 2.0, KOI_FIN, 0.45)
    trace_discs(KOI_P0, (60.0, 880.0), (40.0, 915.0), (30.0, 940.0), 26,
                lambda t: 18.0 * (1.0 - t) + 3.0, KOI_FIN, 0.5)
    # body
    trace_discs(KOI_P0, KOI_P1, KOI_P2, KOI_P3, 170,
                lambda t: KOI_R * koi_profile(t), KOI_BACK)
    # cream belly on the lower side of the body
    for i in range(171):
        t = i / 170.0
        x, y = cubic(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t)
        nx, ny = down_normal(cubic_tangent(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t))
        r = KOI_R * koi_profile(t)
        disc(x + nx * 0.45 * r, y + ny * 0.45 * r, 0.60 * r, KOI_BELLY)
    # thin dark line along the back edge
    for i in range(171):
        t = i / 170.0
        x, y = cubic(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t)
        nx, ny = down_normal(cubic_tangent(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t))
        r = KOI_R * koi_profile(t)
        disc(x - nx * 0.86 * r, y - ny * 0.86 * r, 3.0, KOI_DARK)
    # dorsal fin along the back, mid-body
    for i in range(41):
        t = 0.30 + 0.25 * (i / 40.0)
        x, y = cubic(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t)
        nx, ny = down_normal(cubic_tangent(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t))
        r = KOI_R * koi_profile(t)
        env = math.sin(math.pi * (i / 40.0))
        disc(x - nx * 0.85 * r, y - ny * 0.85 * r, 4.0 + 13.0 * env,
             KOI_FIN, 0.6)
    # eye on the upper side of the head
    ex, ey = KOI_P3[0] + 6.0, KOI_P3[1] - 9.0
    disc(ex, ey, 12.0, (255, 255, 255))
    disc(ex + 2.0, ey + 1.0, 5.5, (20, 16, 12))
    disc(ex - 1.0, ey - 3.0, 2.2, (255, 255, 255))
    # mouth: a short dark curve under the snout
    sx, sy = KOI_P3[0] + 32.0, KOI_P3[1] + 20.0
    for dx, dy in ((0, 0), (4, 2), (8, 3), (12, 3), (16, 2)):
        disc(sx + dx, sy + dy, 2.0, (122, 36, 16))
    # short whiskers curving forward from the snout
    trace_discs((sx, sy), (sx + 18, sy + 8), (sx + 26, sy + 14), (sx + 30, sy + 20),
                12, lambda t: 1.5, KOI_DARK, 0.8)
    trace_discs((sx, sy), (sx + 16, sy + 18), (sx + 22, sy + 30), (sx + 24, sy + 38),
                12, lambda t: 1.5, KOI_DARK, 0.8)


# ---------------------------------------------------------------- spray

SPRAY_Q0 = (110.0, 905.0)
SPRAY_Q1 = (330.0, 580.0)
SPRAY_Q2 = (590.0, 360.0)
SPRAY_Q3 = (830.0, 540.0)


def draw_spray():
    # pale ribbon following the leap, below the fish
    trace_discs(SPRAY_Q0, SPRAY_Q1, SPRAY_Q2, SPRAY_Q3, 170,
                lambda t: 10.0 * (1.0 - 0.6 * t) + 3.0, (191, 227, 255), 0.22)
    # droplets scattered along the ribbon
    for _ in range(55):
        t = rnd()
        x, y = cubic(SPRAY_Q0, SPRAY_Q1, SPRAY_Q2, SPRAY_Q3, t)
        tx, ty = cubic_tangent(SPRAY_Q0, SPRAY_Q1, SPRAY_Q2, SPRAY_Q3, t)
        nx, ny = down_normal((tx, ty))
        off = (rnd() - 0.5) * 46.0
        r = 2.0 + rnd() * 5.0
        disc(x + nx * off, y + ny * off, r, (223, 241, 255), 0.75)
        if rnd() < 0.25:
            disc(x + nx * off - 1.0, y + ny * off - 1.0, 1.2,
                 (255, 255, 255), 0.9)
    # splash burst where the tail left the water
    for _ in range(14):
        ang = rnd() * math.pi * 2.0
        dist = 20.0 + rnd() * 55.0
        disc(KOI_P0[0] + math.cos(ang) * dist,
             KOI_P0[1] + math.sin(ang) * dist,
             2.0 + rnd() * 3.0, (223, 241, 255), 0.8)
    # spray ahead of the head
    for _ in range(10):
        disc(KOI_P3[0] + 30.0 + rnd() * 55.0,
             KOI_P3[1] + 10.0 + rnd() * 45.0,
             2.0 + rnd() * 3.5, (223, 241, 255), 0.8)


# ---------------------------------------------------------------- caption

# 5x7 bitmap font (rows top to bottom, 5 bits each); only the letters used.
FONT = {
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    " ": (0, 0, 0, 0, 0, 0, 0),
}


def draw_text(text, x, y, scale, rgb, shadow):
    """Draw block text; a dark copy offset first gives a crisp edge."""
    for ox, oy in ((scale // 2, scale // 2), (0, 0)):
        col = shadow if (ox, oy) != (0, 0) else rgb
        cx = x + ox
        cy = y + oy
        for ch in text:
            glyph = FONT[ch]
            for row in range(7):
                bits = glyph[row]
                for bit in range(5):
                    if bits & (1 << (4 - bit)):
                        px = cx + bit * scale
                        py = cy + row * scale
                        for yy in range(py, py + scale):
                            set_span(yy, px, px + scale, col)
            cx += 6 * scale


def draw_caption():
    text = "JUMP THE MOON"
    scale = 6
    width = len(text) * 6 * scale - scale
    draw_text(text, (W - width) // 2, 868, scale, (255, 215, 106),
              (40, 20, 60))


# ---------------------------------------------------------------- PNG output


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    prev = bytearray(W * 3)
    for y in range(H):
        row = bytes(fb[y])
        # filter 0 (None)
        cost0 = sum(b if b < 128 else 256 - b for b in row)
        # filter 2 (Up): byte minus the byte above
        up = bytes((a - b) & 0xFF for a, b in zip(row, prev))
        cost2 = sum(b if b < 128 else 256 - b for b in up)
        if cost2 < cost0:
            raw.append(2)
            raw += up
        else:
            raw.append(0)
            raw += row
        prev = bytearray(row)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- main


def render():
    draw_sky()
    draw_stars()
    draw_moon()
    draw_sea()
    draw_spray()
    draw_koi()
    draw_caption()


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    render()
    write_png(os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
