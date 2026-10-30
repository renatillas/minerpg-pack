#!/usr/bin/env python3
"""Generate Apotheosis affix loot entries for RPG Series class gear.

Apotheosis' random affix items (the extra affix item in chests, and the gear some monsters
wear) come from `affix_loot_entries`. It only lists vanilla gear, which is mostly junk in a
class pack. This script adds one entry per RPG Series weapon/armor piece, weighted by world
tier so the class gear tier follows the world tier (tier 1 iron gear in Haven/Venture,
tier 2 diamond gear in Venture/Ascent, tier 3 netherite gear in Summit/Pinnacle, unique
weapons rarely from Summit on), and turns off the vanilla leather/chainmail/gold/stone
entries.

Run:  python3 pack/tools/gen_affix_loot.py <path to a server's config/rpg_series/tag_cache.json>
(tag_cache.json is written by RPG Series at runtime and lists only items that really exist,
so missing optional items, e.g. the empty tier 4, are skipped.)
Writes: pack/kubejs/data/minerpg/affix_loot_entries/rpg/*.json
        pack/kubejs/data/apotheosis/affix_loot_entries/<vanilla>.json (disabled)
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
DATA = os.path.join(ROOT, 'kubejs', 'data')

# RPG loot tier tag -> Apotheosis world tier weights.
TIERS = {
    'tier_1': {'haven': 10, 'frontier': 25, 'ascent': 10},
    'tier_2': {'frontier': 10, 'ascent': 25, 'summit': 10},
    'tier_3': {'summit': 25, 'pinnacle': 15},
}
UNIQUE_WEIGHTS = {'summit': 2, 'pinnacle': 5}  # tier 5 weapons (Arsenal uniques etc.)

# Vanilla entries that only make filler junk next to class gear.
VANILLA_OFF = [
    'leather_helmet', 'leather_chestplate', 'leather_leggings', 'leather_boots',
    'chainmail_helmet', 'chainmail_chestplate', 'chainmail_leggings', 'chainmail_boots',
    'golden_helmet', 'golden_chestplate', 'golden_leggings', 'golden_boots',
    'golden_sword', 'golden_axe', 'golden_pickaxe', 'golden_shovel',
    'stone_sword', 'stone_axe', 'stone_pickaxe', 'stone_shovel', 'turtle_helmet',
    # Shears have no loot category in this pack (staves and wands use that category, see
    # kubejs/data/apotheosis/data_maps/item/loot_category_overrides.json), and Apotheosis
    # rejects entries for items without one.
    'shears',
]


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def entry(item, weights):
    return {
        'type': 'apotheosis:affix_loot_entry',
        'stack': {'count': 1, 'id': item},
        'weights': {tier: {'weight': w} for tier, w in weights.items()},
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    cache = json.load(open(sys.argv[1]))['cache']
    out = os.path.join(DATA, 'minerpg', 'affix_loot_entries', 'rpg')
    if os.path.isdir(out):
        shutil.rmtree(out)
    seen = set()
    count = 0
    for tier, weights in TIERS.items():
        for kind in ('weapons', 'armors'):
            for item in cache.get(f'rpg_series:loot_tier/{tier}_{kind}', []):
                if item in seen:
                    continue
                seen.add(item)
                write(os.path.join(out, item.replace(':', '__') + '.json'), entry(item, weights))
                count += 1
    for item in cache.get('rpg_series:loot_tier/tier_5_weapons', []):
        if item in seen:
            continue
        seen.add(item)
        write(os.path.join(out, item.replace(':', '__') + '.json'), entry(item, UNIQUE_WEIGHTS))
        count += 1
    for name in VANILLA_OFF:
        write(os.path.join(DATA, 'apotheosis', 'affix_loot_entries', name + '.json'),
              {'neoforge:conditions': [{'type': 'neoforge:false'}]})
    print(f'{count} RPG affix loot entries, {len(VANILLA_OFF)} vanilla entries disabled')


if __name__ == '__main__':
    main()
