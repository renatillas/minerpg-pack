#!/usr/bin/env python3
"""Generate the minerpg branding resource pack (title logo, menu backgrounds, pack icon).

Run from anywhere:  python3 pack/tools/gen_brand_pack.py
Writes: pack/resourcepacks/minerpg-look.zip  (a plain resource pack, enabled by default through
config/defaultoptions-common.toml; it sits above Excalibur so our logo wins).

Everything is drawn here from code: an original pixel wordmark "MINERPG" in gold with a dark
outline and drop shadow, warm dark menu backgrounds, and a small pack icon. No third-party art.
Pure Python (zlib + struct), no Pillow needed. The zip uses fixed timestamps so re-running
without changes produces the same bytes (and the same packwiz hash).

Title-screen textures in 1.21.1 (checked in the vanilla client jar):
  textures/gui/title/minecraft.png   1024x256, drawn as 256x44 of a 256x64 sheet -> the logo
                                     lives in the top 1024x176 pixels.
  textures/gui/title/minceraft.png   the rare easter-egg spelling; same image here.
  textures/gui/title/edition.png     512x64 "Java Edition" line under the logo; transparent here.
  textures/gui/menu_background.png, menu_list_background.png and their inworld_ variants: 16x16
                                     tiles drawn behind menus and lists.
The night panorama of the spawn village is NOT here: rendering one needs a game client.
Excalibur ships its own medieval panorama, which shows behind our logo.
"""
import io
import json
import os
import random
import struct
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
OUT = os.path.join(ROOT, 'resourcepacks', 'minerpg-look.zip')
FIXED_TIME = (2026, 10, 31, 0, 0, 0)


# --------------------------------------------------------------------------------------
# Tiny RGBA image + PNG encoder
# --------------------------------------------------------------------------------------
class Image:
    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.px = [list(fill) for _ in range(w * h)]

    def get(self, x, y):
        return self.px[y * self.w + x]

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = list(c)

    def blend(self, x, y, c):
        """Alpha-composite colour c (r,g,b,a) over the pixel."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        r, g, b, a = c
        dr, dg, db, da = self.get(x, y)
        a1, a2 = a / 255.0, da / 255.0
        out = a1 + a2 * (1 - a1)
        if out == 0:
            return
        mix = lambda s, d: int(round((s * a1 + d * a2 * (1 - a1)) / out))
        self.put(x, y, (mix(r, dr), mix(g, dg), mix(b, db), int(round(out * 255))))

    def png(self):
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)
            for x in range(self.w):
                raw.extend(bytes(self.get(x, y)))

        def chunk(kind, data):
            body = kind + data
            return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

        return (b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('>IIBBBBB', self.w, self.h, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
                + chunk(b'IEND', b''))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


# --------------------------------------------------------------------------------------
# The wordmark: an original 8-row pixel alphabet for the seven letters we need
# --------------------------------------------------------------------------------------
GLYPHS = {
    'M': ['XX...XX', 'XXX.XXX', 'XXXXXXX', 'XX.X.XX', 'XX...XX', 'XX...XX', 'XX...XX', 'XX...XX'],
    'I': ['XXXX', '.XX.', '.XX.', '.XX.', '.XX.', '.XX.', '.XX.', 'XXXX'],
    'N': ['XX..XX', 'XXX.XX', 'XXXXXX', 'XX.XXX', 'XX..XX', 'XX..XX', 'XX..XX', 'XX..XX'],
    'E': ['XXXXXX', 'XX....', 'XX....', 'XXXXX.', 'XX....', 'XX....', 'XX....', 'XXXXXX'],
    'R': ['XXXXX.', 'XX..XX', 'XX..XX', 'XXXXX.', 'XX.XX.', 'XX..XX', 'XX..XX', 'XX..XX'],
    'P': ['XXXXX.', 'XX..XX', 'XX..XX', 'XXXXX.', 'XX....', 'XX....', 'XX....', 'XX....'],
    'G': ['.XXXX.', 'XX..XX', 'XX....', 'XX....', 'XX.XXX', 'XX..XX', 'XX..XX', '.XXXX.'],
}

GOLD_TOP = (255, 236, 150, 255)
GOLD_MID = (232, 176, 58, 255)
GOLD_LOW = (150, 88, 20, 255)
OUTLINE = (40, 22, 10, 255)
SHADOW = (0, 0, 0, 150)


def word_mask(word):
    """Grid of booleans (rows x cols) for the word, one empty column between letters."""
    rows = 8
    grid = [[] for _ in range(rows)]
    for i, ch in enumerate(word):
        g = GLYPHS[ch]
        for r in range(rows):
            if i:
                grid[r].append(False)
            grid[r].extend(c == 'X' for c in g[r])
    return grid


def draw_wordmark(img, word, cell, ox, oy, outline=5, shadow=8):
    grid = word_mask(word)
    rows, cols = len(grid), len(grid[0])
    filled = lambda r, c: 0 <= r < rows and 0 <= c < cols and grid[r][c]
    w, h = cols * cell, rows * cell
    inside = [[filled(y // cell, x // cell) for x in range(w)] for y in range(h)]

    def near(x, y, d):
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and inside[yy][xx]:
                    return True
        return False

    # Drop shadow, then outline, then the gold letters with a bevel.
    for y in range(-outline, h + outline + shadow):
        for x in range(-outline, w + outline):
            if near(x, y - shadow, outline):
                img.blend(ox + x, oy + y, SHADOW)
    for y in range(-outline, h + outline):
        for x in range(-outline, w + outline):
            if near(x, y, outline):
                img.put(ox + x, oy + y, OUTLINE)
    bevel = max(2, cell // 6)
    for y in range(h):
        t = y / (h - 1)
        base = lerp(GOLD_TOP, GOLD_MID, t / 0.5) if t < 0.5 else lerp(GOLD_MID, GOLD_LOW, (t - 0.5) / 0.5)
        for x in range(w):
            if not inside[y][x]:
                continue
            r, c = y // cell, x // cell
            col = base
            # Light top edge and dark bottom/right edge on each exposed side of a cell.
            if y % cell < bevel and not filled(r - 1, c):
                col = lerp(col, (255, 250, 220, 255), 0.6)
            elif y % cell >= cell - bevel and not filled(r + 1, c):
                col = lerp(col, (90, 45, 8, 255), 0.6)
            elif x % cell >= cell - bevel and not filled(r, c + 1):
                col = lerp(col, (110, 60, 10, 255), 0.4)
            elif x % cell < bevel and not filled(r, c - 1):
                col = lerp(col, (255, 240, 190, 255), 0.35)
            img.put(ox + x, oy + y, col)
    return w, h


def logo():
    img = Image(1024, 256)
    word = 'MINERPG'
    cell = 19
    cols = len(word_mask(word)[0])
    w, h = cols * cell, 8 * cell
    # The game shows only the top 176 pixel rows (256x44 of a 256x64 sheet).
    ox = (1024 - w) // 2
    oy = (176 - h - 8) // 2
    draw_wordmark(img, word, cell, ox, oy)
    return img


def tile(base, alpha, seed, grain=10):
    """16x16 menu background: warm dark brown with a faint wood-like grain."""
    rnd = random.Random(seed)
    img = Image(16, 16)
    for y in range(16):
        row_shift = rnd.randint(-grain // 2, grain // 2)
        for x in range(16):
            n = rnd.randint(-grain // 3, grain // 3) + row_shift
            c = tuple(max(0, min(255, base[i] + n)) for i in range(3))
            img.put(x, y, c + (alpha,))
    return img


def icon():
    img = Image(64, 64, (34, 22, 14, 255))
    for y in range(64):
        for x in range(64):
            if x in (0, 63) or y in (0, 63):
                img.put(x, y, (120, 74, 20, 255))
    # One big "M" from the wordmark alphabet.
    draw_wordmark(img, 'M', 6, (64 - 7 * 6) // 2, (64 - 8 * 6) // 2 - 2, outline=2, shadow=3)
    return img


def main():
    files = {
        'pack.mcmeta': json.dumps({'pack': {
            'pack_format': 34,
            'description': '§6minerpg§7 title logo and menus',
        }}, indent=2).encode(),
        'pack.png': icon().png(),
        'assets/minecraft/textures/gui/title/minecraft.png': logo().png(),
        'assets/minecraft/textures/gui/title/minceraft.png': logo().png(),
        'assets/minecraft/textures/gui/title/edition.png': Image(512, 64).png(),
        # Menus outside a world (over the panorama) and lists (worlds, servers, packs).
        'assets/minecraft/textures/gui/menu_background.png': tile((44, 30, 20), 150, 1).png(),
        'assets/minecraft/textures/gui/menu_list_background.png': tile((32, 22, 15), 200, 2).png(),
        # The same screens opened inside a world (pause menu, options): lighter, the game shows through.
        'assets/minecraft/textures/gui/inworld_menu_background.png': tile((44, 30, 20), 110, 3).png(),
        'assets/minecraft/textures/gui/inworld_menu_list_background.png': tile((32, 22, 15), 150, 4).png(),
    }
    for name in ('minecraft.png', 'minceraft.png', 'edition.png'):
        files[f'assets/minecraft/textures/gui/title/{name}.mcmeta'] = json.dumps({'texture': {'blur': True}}).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[name])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(buf.getvalue())
    print(f'{OUT}: {len(files)} files, {len(buf.getvalue())} bytes')


if __name__ == '__main__':
    main()
