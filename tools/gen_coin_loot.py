#!/usr/bin/env python3
"""Generate coin loot (RPG Coins) for chests and bosses.

Coins are the pack's money (kubejs/server_scripts/minerpg_coins.js): job levels and quests pay Gold Coins, and
this adds coins to loot on top, so over a career loot gives about as much as levels and quests together.

  - ordinary chests (villages, ruins, outposts, camps...): mostly Copper, some Iron, rarely Gold;
  - dungeon chests (dungeon and stronghold mods, temples, bastions, ancient cities...): Iron and Gold;
  - bosses (#minerpg:boss, killed by a player): Gold and Iron.

NeoForge's loot_table_id condition only matches exact ids, so the chest lists are read from the mod jars.

Run:  python3 pack/tools/gen_coin_loot.py <path to a server's mods folder>
Writes: pack/kubejs/data/minerpg/loot_table/coins/*.json
        pack/kubejs/data/minerpg/loot_modifiers/coins_*.json (+ entries in neoforge's global_loot_modifiers.json)
"""
import glob
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
DATA = os.path.join(ROOT, 'kubejs', 'data')

# Vanilla's chest tables are not in the mods folder.
VANILLA_CHESTS = [
    'abandoned_mineshaft', 'ancient_city', 'ancient_city_ice_box', 'bastion_bridge', 'bastion_hoglin_stable',
    'bastion_other', 'bastion_treasure', 'buried_treasure', 'desert_pyramid', 'end_city_treasure', 'igloo_chest',
    'jungle_temple', 'nether_bridge', 'pillager_outpost', 'ruined_portal', 'shipwreck_map', 'shipwreck_supply',
    'shipwreck_treasure', 'simple_dungeon', 'stronghold_corridor', 'stronghold_crossing', 'stronghold_library',
    'underwater_ruin_big', 'underwater_ruin_small', 'woodland_mansion',
    'trial_chambers/corridor', 'trial_chambers/entrance', 'trial_chambers/intersection',
    'trial_chambers/intersection_barrel', 'trial_chambers/supply', 'trial_chambers/reward',
    'trial_chambers/reward_common', 'trial_chambers/reward_rare', 'trial_chambers/reward_unique',
    'trial_chambers/reward_ominous', 'trial_chambers/reward_ominous_common', 'trial_chambers/reward_ominous_rare',
    'trial_chambers/reward_ominous_unique',
    'village/village_armorer', 'village/village_butcher', 'village/village_cartographer',
    'village/village_desert_house', 'village/village_fisher', 'village/village_fletcher', 'village/village_mason',
    'village/village_plains_house', 'village/village_savanna_house', 'village/village_shepherd',
    'village/village_snowy_house', 'village/village_taiga_house', 'village/village_tannery',
    'village/village_temple', 'village/village_toolsmith', 'village/village_weaponsmith',
]
# Vanilla chests that count as dungeons.
VANILLA_DUNGEON = re.compile(r'^(simple_dungeon|stronghold_.*|ancient_city.*|bastion_.*|end_city_treasure|'
                             r'woodland_mansion|nether_bridge|desert_pyramid|jungle_temple|buried_treasure|'
                             r'trial_chambers/reward.*)$')
# Mods whose chests are all dungeon chests.
DUNGEON_MODS = {'cataclysm', 'mowziesmobs', 'apotheosis', 'betterstrongholds', 'betterfortresses',
                'betterdeserttemples', 'betterjungletemples', 'betteroceanmonuments', 'dungeons_arise'}
# Tables that are only pulled into other tables (class mods' injections, Farmer's Delight's additions) or are no
# real chest: coins there would come twice or from nowhere.
SKIP_MODS = {'lne_wizards', 'lne_archers', 'lne_paladins', 'lne_rogues', 'farmersdelight', 'lootr'}
SKIP_TABLES = {'minecraft:chests/spawn_bonus_chest', 'minecraft:chests/jungle_temple_dispenser'}


def coin(item, lo, hi):
    return {'type': 'minecraft:item', 'name': item,
            'functions': [{'function': 'minecraft:set_count', 'count': {'type': 'minecraft:uniform', 'min': lo, 'max': hi}}]}


def pool(chance, entry):
    p = {'rolls': 1, 'entries': [entry]}
    if chance < 1:
        p['conditions'] = [{'condition': 'minecraft:random_chance', 'chance': chance}]
    return p


# Expected gold per roll: ordinary ~0.18, dungeon ~0.8, boss ~5.5 (an Iron Coin is 1/9 gold, a Copper Coin 1/81).
TABLES = {
    'ordinary_chest': [pool(0.75, coin('coins:copper_coin', 3, 8)), pool(0.35, coin('coins:iron_coin', 1, 3)),
                       pool(0.05, coin('coins:gold_coin', 1, 1))],
    'dungeon_chest': [pool(0.5, coin('coins:copper_coin', 4, 10)), pool(0.7, coin('coins:iron_coin', 2, 5)),
                      pool(0.35, coin('coins:gold_coin', 1, 2))],
    'boss': [pool(1, coin('coins:gold_coin', 3, 6)), pool(1, coin('coins:iron_coin', 2, 6))],
}


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def chest_tables(mods):
    """All chest loot table ids in the mods folder plus vanilla's."""
    ids = {'minecraft:chests/' + c for c in VANILLA_CHESTS}
    for jar in glob.glob(os.path.join(mods, '*.jar')):
        try:
            names = zipfile.ZipFile(jar).namelist()
        except zipfile.BadZipFile:
            continue
        for name in names:
            m = re.match(r'data/([^/]+)/loot_table/(chests/.+)\.json$', name)
            if m:
                ids.add(f'{m[1]}:{m[2]}')
    return sorted(i for i in ids if i.split(':')[0] not in SKIP_MODS and i not in SKIP_TABLES)


def is_dungeon(table):
    ns, path = table.split(':')
    if ns in DUNGEON_MODS:
        return True
    return ns == 'minecraft' and bool(VANILLA_DUNGEON.match(path[len('chests/'):]))


def any_table(ids):
    return [{'condition': 'minecraft:any_of',
             'terms': [{'condition': 'neoforge:loot_table_id', 'loot_table_id': i} for i in ids]}]


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    tables = chest_tables(sys.argv[1])
    dungeon = [t for t in tables if is_dungeon(t)]
    ordinary = [t for t in tables if not is_dungeon(t)]
    for name, pools in TABLES.items():
        write(os.path.join(DATA, 'minerpg', 'loot_table', 'coins', name + '.json'),
              {'type': 'minecraft:chest' if name != 'boss' else 'minecraft:entity', 'pools': pools})
    mods = os.path.join(DATA, 'minerpg', 'loot_modifiers')
    write(os.path.join(mods, 'coins_ordinary_chests.json'),
          {'type': 'neoforge:add_table', 'conditions': any_table(ordinary), 'table': 'minerpg:coins/ordinary_chest'})
    write(os.path.join(mods, 'coins_dungeon_chests.json'),
          {'type': 'neoforge:add_table', 'conditions': any_table(dungeon), 'table': 'minerpg:coins/dungeon_chest'})
    write(os.path.join(mods, 'coins_bosses.json'), {
        'type': 'neoforge:add_table',
        'conditions': [{'condition': 'minecraft:entity_properties', 'entity': 'this', 'predicate': {'type': '#minerpg:boss'}},
                       {'condition': 'minecraft:killed_by_player'}],
        'table': 'minerpg:coins/boss'})
    glm = os.path.join(DATA, 'neoforge', 'loot_modifiers', 'global_loot_modifiers.json')
    d = json.load(open(glm))
    for e in ('minerpg:coins_ordinary_chests', 'minerpg:coins_dungeon_chests', 'minerpg:coins_bosses'):
        if e not in d['entries']:
            d['entries'].append(e)
    write(glm, d)
    print(f'coin loot: {len(ordinary)} ordinary chests, {len(dungeon)} dungeon chests, bosses')


if __name__ == '__main__':
    main()
