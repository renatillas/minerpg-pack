#!/usr/bin/env python3
"""Trophy items for the pack 1.5.5 bosses: their icons and names.

The trophies themselves are registered in kubejs/startup_scripts/minerpg_items.js, handed out at the kill in
kubejs/server_scripts/minerpg_soft_locks.js (BOSS_DROPS), described in kubejs/client_scripts/minerpg_tooltips.js,
checked by the quests (tools/gen_quests.py) and the Field Guide (tools/gen_handbook.py). Keep the keys in step.

Run:  python3 pack/tools/gen_trophy_icons.py
Writes: pack/kubejs/assets/minerpg/textures/item/trophy_<key>.png (16x16, drawn here: original art)
        item.minerpg.trophy_<key> names in pack/kubejs/assets/minerpg/lang/en_us.json
"""
import json
import os

from spell_lib import png

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
TEXTURES = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'textures', 'item')
LANG = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'lang', 'en_us.json')

# key -> (name, shape, main color, highlight color)
TROPHIES = {
    'sandworm': ('Dune Fang', 'fang', (214, 182, 120), (255, 236, 180)),
    'yeti': ('Hoarfrost Pelt', 'pelt', (210, 226, 240), (255, 255, 255)),
    'kraken': ('Abyssal Ink', 'drop', (40, 46, 96), (120, 140, 220)),
    'infernal_dragon': ('Cinder Scale', 'scale', (190, 64, 32), (255, 170, 60)),
    'underworld_knight': ('Oathbreaker Seal', 'seal', (96, 70, 140), (200, 170, 255)),
    'corrupted_champion': ("Champion's Tarnished Crest", 'crest', (120, 110, 90), (200, 190, 150)),
    'night_lich': ('Phylactery Shard', 'shard', (60, 160, 170), (170, 255, 250)),
    'gauntlet': ('Gauntlet Core', 'core', (150, 40, 40), (255, 120, 90)),
    'void_blossom': ('Void Petal', 'petal', (110, 50, 150), (220, 140, 255)),
    'obsidilith': ('Obsidian Heartstone', 'core', (40, 30, 60), (170, 120, 230)),
}


def inside(shape, x, y):
    if shape == 'fang':
        return abs(x) <= 3 - (y + 6) / 4.5 and -6 <= y <= 6
    if shape == 'pelt':
        return (abs(x) <= 5 and -3 <= y <= 4) or (abs(x) <= 2 and -6 <= y <= 6)
    if shape == 'drop':
        return (x * x + (y - 2) ** 2 <= 16) or (abs(x) <= (y + 6) / 2.2 and -6 <= y <= 2)
    if shape == 'scale':
        return x * x / 25 + (y + 1) ** 2 / 36 <= 1 and y <= 4
    if shape == 'seal':
        return abs(x) + abs(y) <= 6
    if shape == 'crest':
        return abs(x) <= 5 and -5 <= y <= 2 or (abs(x) <= 5 - (y - 2) and 2 <= y <= 6)
    if shape == 'shard':
        return abs(x) <= 2.5 - abs(y) / 3 and abs(y) <= 6.5
    if shape == 'core':
        return x * x + y * y <= 26
    if shape == 'petal':
        return (x * x) / 9 + (y * y) / 42 <= 1 or (x * x) / 42 + (y * y) / 9 <= 1
    raise ValueError(shape)


def draw(path, shape, color, light):
    rows = []
    for py in range(16):
        row = []
        for px in range(16):
            x, y = px - 7.5, py - 7.5
            if not inside(shape, x, y):
                row.append((0, 0, 0, 0))
                continue
            edge = not all(inside(shape, x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                row.append((max(0, color[0] // 3), max(0, color[1] // 3), max(0, color[2] // 3), 255))
                continue
            t = max(0.0, min(1.0, 0.5 - (x + y) / 14))  # light from the top left
            row.append(tuple(int(c + (l - c) * t * 0.8) for c, l in zip(color, light)) + (255,))
        rows.append(row)
    png(path, rows)


def main():
    os.makedirs(TEXTURES, exist_ok=True)
    lang = json.load(open(LANG, encoding='utf-8'))
    for key, (name, shape, color, light) in TROPHIES.items():
        draw(os.path.join(TEXTURES, f'trophy_{key}.png'), shape, color, light)
        lang[f'item.minerpg.trophy_{key}'] = name
    with open(LANG, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(lang.items())), f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'{len(TROPHIES)} trophies')


if __name__ == '__main__':
    main()
