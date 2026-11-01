#!/usr/bin/env python3
"""Generate the minerpg quest book (FTB Quests SNBT) and its helper datapack files.

Run from anywhere:  python3 pack/tools/gen_quests.py
Writes:
  pack/config/ftbquests/quests/            data.snbt, chapter_groups.snbt, chapters/*.snbt,
                                           reward_tables/*.snbt, lang/en_us.snbt
  pack/kubejs/data/minerpg/function/kit/   one function per class kit (choice reward)
  pack/kubejs/data/minerpg/advancement/    hidden helper advancements used by quest tasks

Quest object ids are derived from stable keys (sha1), so re-running keeps ids (and player
progress) stable as long as a quest's key does not change. This folder is excluded from the
pack by pack/.packwizignore.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
QUESTS = os.path.join(ROOT, 'config', 'ftbquests', 'quests')
DATA = os.path.join(ROOT, 'kubejs', 'data')


# --------------------------------------------------------------------------------------
# SNBT writing (FTB style: one entry per line, no commas)
# --------------------------------------------------------------------------------------
class Long(int):
    pass


class Double(float):
    pass


class Float(float):
    pass


def q(s):
    return json.dumps(s, ensure_ascii=False)


def snbt(value, indent=0):
    pad = '\t' * indent
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, Long):
        return f'{int(value)}L'
    if isinstance(value, Double):
        return f'{float(value)}d'
    if isinstance(value, Float):
        return f'{float(value)}f'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f'{value}d'
    if isinstance(value, str):
        return q(value)
    if isinstance(value, dict):
        if not value:
            return '{ }'
        lines = ['{']
        for k in sorted(value):
            key = k if all(c.isalnum() or c in '_' for c in k) else q(k)
            lines.append(f'{pad}\t{key}: {snbt(value[k], indent + 1)}')
        lines.append(pad + '}')
        return '\n'.join(lines)
    if isinstance(value, list):
        if not value:
            return '[ ]'
        if all(isinstance(v, str) for v in value):
            lines = ['[']
            for v in value:
                lines.append(f'{pad}\t{q(v)}')
            lines.append(pad + ']')
            return '\n'.join(lines)
        lines = ['[']
        for v in value:
            lines.append(f'{pad}\t{snbt(v, indent + 1)}')
        lines.append(pad + ']')
        return '\n'.join(lines)
    raise TypeError(value)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
        if not text.endswith('\n'):
            f.write('\n')


def oid(key):
    """Stable 16-hex-digit id that fits in a signed long (first digit 1-7)."""
    h = int(hashlib.sha1(key.encode()).hexdigest()[:16], 16) & 0x7FFFFFFFFFFFFFFF
    if h < 0x1000000000000000:
        h |= 0x1000000000000000
    return f'{h:016X}'


LANG = {}


def lang(kind, ident, sub, text):
    LANG[f'{kind}.{ident}.{sub}'] = text


# --------------------------------------------------------------------------------------
# Task / reward helpers
# --------------------------------------------------------------------------------------
def stack(item, count=1, components=None):
    s = {'id': item, 'count': count}
    if components:
        s['components'] = components
    return s


def t_item(item, count=1, components=None, title=None):
    t = {'type': 'item', 'item': stack(item, 1, components)}
    if count > 1:
        t['count'] = Long(count)
    if title:
        t['_title'] = title
    return t


def t_adv(adv, title=None):
    t = {'type': 'advancement', 'advancement': adv, 'criterion': ''}
    if title:
        t['_title'] = title
    return t


def t_check(title):
    return {'type': 'checkmark', '_title': title}


def t_kill(entity=None, count=1, tag=None, title=None):
    t = {'type': 'kill', 'entity': entity or 'minecraft:zombie', 'value': Long(count)}
    if tag:
        t['entityTypeTag'] = tag
    if title:
        t['_title'] = title
    return t


def t_dim(dim, title=None):
    t = {'type': 'dimension', 'dimension': dim}
    if title:
        t['_title'] = title
    return t


def t_struct(structure, title=None):
    t = {'type': 'structure', 'structure': structure}
    if title:
        t['_title'] = title
    return t


def r_item(item, count=1, components=None):
    return {'type': 'item', 'item': stack(item, 1, components), 'count': count}


def r_xp(xp):
    return {'type': 'xp', 'xp': xp}


def r_levels(levels):
    return {'type': 'xp_levels', 'xp_levels': levels}


def r_cmd(command, title=None):
    """Command reward, run as the player (so @s works) with op permission, silently."""
    r = {'type': 'command', 'command': command, 'permission_level': 2, 'silent': True}
    if title:
        r['_title'] = title
    return r


# +1 Class Skills talent point. Kills stop giving class points at 9 (level_limit in
# kubejs/data/skill_tree_rpgs/puffish_skills/categories/class_skills/experience.json); the last
# four come from the chapter bosses (Harbinger, Netherite Monstrosity, Ignis, Ender Guardian).
def r_talent_point():
    return r_cmd('/puffish_skills points add @s skill_tree_rpgs:class_skills 1 minerpg:bosses', '+1 talent point')


# Gold Coins (RPG Coins), the pack's money: the Jobs menu spends the coins a player carries
# (kubejs/server_scripts/minerpg_coins.js).
def r_coins(amount):
    return r_item('coins:gold_coin', amount)


# One Spell Infinity book (spells stop using runes). It is not on the enchanting table or in
# random loot (kubejs/server_scripts/minerpg_enchanting.js).
SPELL_INFINITY_BOOK = {'minecraft:stored_enchantments': {'levels': {'spell_engine:spell_infinity': 1}}}


# --------------------------------------------------------------------------------------
# Class kits ("Choose your calling" choice reward)
# --------------------------------------------------------------------------------------
def book(pool):
    ns, path = pool.split(':')
    return {
        'minecraft:item_name': json.dumps({'translate': f'item.{ns}.{path}'}),
        'spell_engine:item_model': f'{ns}:item/{path}',
        'spell_engine:spell_container': {'pool': pool},
    }


# (key, kit title, book pool, weapon, armor piece, extra stacks [(item, count)])
KITS = [
    ('arcane_wizard', 'Arcane Wizard', 'wizards:spell_book/arcane', 'wizards:wand_arcane', 'wizards:wizard_robe_chest', [('runes:arcane_stone', 32)]),
    ('fire_wizard', 'Fire Wizard', 'wizards:spell_book/fire', 'wizards:wand_fire', 'wizards:wizard_robe_chest', [('runes:fire_stone', 32)]),
    ('frost_wizard', 'Frost Wizard', 'wizards:spell_book/frost', 'wizards:wand_frost', 'wizards:wizard_robe_chest', [('runes:frost_stone', 32)]),
    ('water_mage', 'Water Mage', 'elemental_wizards_rpg:spell_book/aqua', 'elemental_wizards_rpg:wand_aqua', 'elemental_wizards_rpg:elemental_chest', [('mrpg_lib:aqua_stone', 32)]),
    ('earth_mage', 'Earth Mage', 'elemental_wizards_rpg:spell_book/terra', 'elemental_wizards_rpg:wand_terra', 'elemental_wizards_rpg:elemental_chest', [('mrpg_lib:terra_stone', 32)]),
    ('wind_mage', 'Wind Mage', 'elemental_wizards_rpg:spell_book/wind', 'elemental_wizards_rpg:wand_wind', 'elemental_wizards_rpg:elemental_chest', [('mrpg_lib:storm_stone', 32)]),
    ('paladin', 'Paladin', 'paladins:spell_book/paladin', 'paladins:iron_mace', 'paladins:paladin_armor_chest', [('runes:healing_stone', 32)]),
    ('priest', 'Priest', 'paladins:spell_book/priest', 'paladins:holy_wand', 'paladins:priest_robe_chest', [('runes:healing_stone', 32)]),
    ('rogue', 'Rogue', 'rogues:spell_book/rogue', 'rogues:iron_dagger', 'rogues:rogue_armor_chest', []),
    ('warrior', 'Warrior', 'rogues:spell_book/warrior', 'rogues:iron_double_axe', 'rogues:warrior_armor_chest', []),
    ('berserker', 'Berserker', 'berserker_rpg:spell_book/berserker', 'berserker_rpg:iron_berserker_axe', 'berserker_rpg:wildling_chest', []),
    ('forcemaster', 'Forcemaster', 'forcemaster_rpg:spell_book/forcemaster', 'forcemaster_rpg:iron_knuckle', 'forcemaster_rpg:oriene_chest', []),
    ('archer', 'Archer', 'archers:spell_book/archer', 'archers:composite_longbow', 'archers:archer_armor_chest', [('minecraft:arrow', 64)]),
    ('deadeye', 'Deadeye', 'archers_expansion:spell_book/deadeye', 'minecraft:bow', 'archers_expansion:deadeye_chest', [('minecraft:arrow', 64)]),
    ('tundra_hunter', 'Tundra Hunter', 'archers_expansion:spell_book/tundra_hunter', 'minecraft:bow', 'archers_expansion:tundra_hunter_chest', [('minecraft:arrow', 64)]),
    ('war_archer', 'War Archer', 'archers_expansion:spell_book/war_archer', 'archers:rapid_crossbow', 'archers_expansion:war_archer_chest', [('minecraft:arrow', 64)]),
    ('bard', 'Bard', 'bards_rpg:spell_book/bard', 'bards_rpg:wooden_lute', 'bards_rpg:entertainer_garb_chest', []),
]


# One flavour line per kit, shown in gray in chat when the kit is claimed (before the gold line).
# Original text: second person, short, in-world.
KIT_FLAVOR = {
    'arcane_wizard': 'You bend raw magic into shape. Keep your distance and let the arcane do the talking.',
    'fire_wizard': 'You are the reason the room is warm. Burn what charges you, then burn what is left.',
    'frost_wizard': 'Slow them, then shatter them. Nothing reaches you through the ice.',
    'water_mage': 'The tide answers to you. Push your foes back and wash your friends clean.',
    'earth_mage': 'Stone listens when you speak. Stand your ground, and the ground stands with you.',
    'wind_mage': 'You are never where they swing. Strike on the gust, and be gone.',
    'paladin': 'You stand in front so the others do not have to. Hold the line; the light holds you.',
    'priest': 'Your friends get back up because you are there. Stay behind them and keep them standing.',
    'rogue': 'The first blow is the one that counts. Strike from the shadows and leave before they turn.',
    'warrior': 'You go in first and come out last. Swing wide and let them come to you.',
    'berserker': 'Every blow feeds your fury. Get close, stay close, and do not stop.',
    'forcemaster': 'No blade, no bow, no need. Your fists carry the weight of a storm.',
    'archer': 'One arrow, one answer. Find high ground and make every shot count.',
    'deadeye': 'Patience kills. Wait for the opening, then end it from afar.',
    'tundra_hunter': 'The cold is your hunting ground. Slow your prey, then bring it down.',
    'war_archer': 'A crossbow, a steady hand and a hail of bolts. Hold the line from range.',
    'bard': 'Your song carries the party. Play them stronger, and let the rhythm cut down the rest.',
}
assert set(KIT_FLAVOR) == {k[0] for k in KITS}, 'every kit needs exactly one flavour line'


def components_arg(components):
    parts = []
    for k, v in components.items():
        if isinstance(v, dict):
            inner = ','.join(f'{ik}:{json.dumps(iv)}' for ik, iv in v.items())
            parts.append(f'{k}={{{inner}}}')
        elif k == 'minecraft:item_name':
            parts.append(f"{k}='{v}'")
        else:
            parts.append(f'{k}={json.dumps(v)}')
    return '[' + ','.join(parts) + ']'


def write_kit_functions():
    folder = os.path.join(DATA, 'minerpg', 'function', 'kit')
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    for key, title, pool, weapon, armor, extras in KITS:
        lines = [
            f'# minerpg class kit: {title}. Run by the "Choose your calling" quest reward (as the player).',
            f'give @s spell_engine:spell_book{components_arg(book(pool))} 1',
            f'give @s {weapon} 1',
            f'give @s {armor} 1',
        ]
        for item, count in extras:
            lines.append(f'give @s {item} {count}')
        # Opens this class's row in the Your Calling tab (kubejs/server_scripts/minerpg_calling.js grants it too).
        lines.append(f'advancement grant @s only minerpg:calling/{key}/start')
        lines.append('tellraw @s ' + json.dumps({'text': KIT_FLAVOR[key], 'color': 'gray', 'italic': True}))
        lines.append('tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}')
        write(os.path.join(folder, f'{key}.mcfunction'), '\n'.join(lines))


# --------------------------------------------------------------------------------------
# Helper advancements (no display: invisible in the advancement screen)
# --------------------------------------------------------------------------------------
def adv(path, criteria, any_of=False):
    body = {'criteria': criteria}
    if any_of:
        body['requirements'] = [sorted(criteria)]
    write(os.path.join(DATA, 'minerpg', 'advancement', path + '.json'), json.dumps(body, indent=2))
    return 'minerpg:' + path


ADV = {}

# Root skills of the Skill Tree categories (from skill_tree_rpgs and mrpgc_skill_tree data).
TALENT_ROOTS = {"weapon_skills": ["hdp8z71mlgffw17t", "o5e8ipv2xtpeksec", "43fud5gyn1kww7k3", "fa5tmn9q8n2ujruy", "paab7o9iixjwuqdj", "ywy3uz6mt474uxcu", "etdoq234nbbk9jmb", "9a4ajj9s55z980hm", "8jeweqbszxdkjec1", "ilkpz2udlubebc6r", "9pokx13bowgou220", "6taxz5gbljn3xfku", "pkne4ano08eqcy4s", "y1a66xz5i124mfmx", "3oqwa67ju4z15ibv", "2fmdz7g1n58lv5tc", "4hcdz3kjdgfthpe9", "kjhwog5cvu0fd423", "t99odhklai0v0udr", "rvwkoplyotazu3n5", "8pfkxajvoxi9hm11", "jg4rdekpojjpqgzp", "3gd4z8ipv6dd762q", "eg55qphw7cctd24u", "oix3o2x7dfazvtzd", "j0u80h45ydvy095x", "w7y0zhqc44m1s3jh", "7v4350xjc6abuhzf", "s3ctqevzq5b784e6", "187m2j16rk4qjyn9", "9dseezauf4am1g09", "soavniyhqv88lhk6", "u4lc6n44j2s94i63", "74lv63m06glo2z4i", "gijhckxjzq2o74dr", "8isy9vsrob80930a", "i1ysm27ti2hox23u", "p5msloq46sdpdjki", "gcmqzfk0v41xdf5u", "fu5xkfmn8ip0bpiu", "lky31jjducya2sbe"], "class_skills": ["rinftzrm9ta3baw4", "vlk9z73h53bx2if3", "859rwa4j1tbw2qs7", "apwqaumpk4dhakie", "7fs13k83hcuhzjkk", "lk37egonho34cey2", "5qc3hkud5vtm6xaw", "ysh5ghgnzszqbi39", "8aixa7er1htsbd9a", "vlxhkx7zsfqwqx66", "cqray6yfemf8au4q", "nbd4thedgpfpztaj", "r7vtgvr1ujnnv2od", "5zb4m5r2slga9c7e", "cmrh2mlkna5uqfog", "5ubm74e5m5vhz773", "b7p70wd9hp5bh4ae", "qr4fdarqqqm5ifoa", "m1pc5vz73nx4b28c", "akyr8k2dv9xsy70c", "418rsvnd17egwkse", "tdimeso8ajcwiygp", "ov6ag9tjdhsmldil", "63gwys64onqg00ry", "e5ljj7jx6pmdjatf"]}


def write_advancements():
    folder = os.path.join(DATA, 'minerpg', 'advancement')
    # Only our own subfolders: advancement/field_guide/ belongs to tools/gen_handbook.py.
    for sub in ('tutorial', 'jobs', 'tour', 'calling', 'guide'):
        if os.path.isdir(os.path.join(folder, sub)):
            shutil.rmtree(os.path.join(folder, sub))
    ADV['cast'] = adv('tutorial/cast_spell', {'cast': {'trigger': 'spell_engine:spell_cast', 'conditions': {}}})
    ADV['bind'] = adv('tutorial/bind_spell', {'bind': {'trigger': 'spell_engine:spell_binding', 'conditions': {}}})
    # The skill_unlocked trigger needs an exact category and skill, so list every root (first)
    # skill of both Skill Tree categories (base + More RPG Classes changes); any one completes it.
    talent = {}
    for category, skills in TALENT_ROOTS.items():
        for skill in skills:
            talent[f'{category}_{skill}'] = {'trigger': 'puffish_skills:skill_unlocked', 'conditions': {
                'category': f'skill_tree_rpgs:{category}', 'skill': skill}}
    ADV['talent'] = adv('tutorial/unlock_talent', talent, any_of=True)
    ADV['runes'] = adv('tutorial/craft_runes', {'runes': {'trigger': 'minecraft:inventory_changed', 'conditions': {'items': [{'items': [
        'runes:arcane_stone', 'runes:fire_stone', 'runes:frost_stone', 'runes:healing_stone', 'runes:lightning_stone',
        'runes:soul_stone', 'mrpg_lib:aqua_stone', 'mrpg_lib:terra_stone', 'mrpg_lib:storm_stone']}]}}})
    ADV['waystone'] = adv('tutorial/use_waystone', {'use': {'trigger': 'minecraft:any_block_use', 'conditions': {
        'location': [{'condition': 'minecraft:location_check', 'predicate': {'block': {'blocks': '#waystones:waystones'}}}]}}})
    # Job starters.
    ADV['alchemist'] = adv('jobs/alchemist', {'brew': {'trigger': 'minecraft:brewed_potion', 'conditions': {}}})
    # Job milestones and "made a job-gated item": granted by the Arc actions that
    # pack/tools/gen_jobs.py writes (via /minerpg_jobs grant), never by a criterion.
    for level in (10, 20, 30):
        ADV[f'job_level_{level}'] = adv(f'jobs/level_{level}', {'granted': {'trigger': 'minecraft:impossible'}})
    ADV['job_gated_craft'] = adv('jobs/gated_craft', {'granted': {'trigger': 'minecraft:impossible'}})
    # Village tour: trade with a class merchant (matched by the villager's profession).
    def trade(profession):
        return {'trigger': 'minecraft:villager_trade', 'conditions': {'villager': {
            'nbt': '{VillagerData:{profession:"%s"}}' % profession}}}
    for key, professions in MERCHANTS.items():
        ADV['trade_' + key] = adv('tour/' + key, {p.split(':')[1]: trade(p) for p in professions}, any_of=True)
    # Your Calling: one "has the class" advancement per kit (granted by the kit function and the tome scan), and the
    # "has an item" tasks of the Calling and guide tabs.
    for key in CALLING:
        adv(f'calling/{key}/start', {'granted': {'trigger': 'minecraft:impossible'}})
    for path, (criteria, any_of) in HAS_ADV.items():
        adv(path, criteria, any_of=any_of)


# --------------------------------------------------------------------------------------
# Structure tags used by "find a ..." quest tasks
# --------------------------------------------------------------------------------------
TAVERN_WOODS = ['acacia', 'birch', 'cherry', 'dark_oak', 'desert', 'jungle', 'mangrove', 'oak', 'snowy', 'spruce', 'swamp']
STRUCTURE_TAGS = {
    'taverns': [f'nova_structures:tavern_{w}' for w in TAVERN_WOODS],
    'small_dungeons': ['betterdungeons:skeleton_dungeon', 'betterdungeons:zombie_dungeon', 'betterdungeons:spider_dungeon',
                       'betterdungeons:small_dungeon', 'nova_structures:undead_crypt', 'nova_structures:creeping_crypt'],
    'wildlands_dungeons': ['dungeons_arise:' + n for n in [
        'abandoned_temple', 'aviary', 'bandit_towers', 'bandit_village', 'bathhouse', 'ceryneian_hind', 'coliseum',
        'foundry', 'giant_mushroom', 'heavenly_challenger', 'heavenly_conqueror', 'heavenly_rider', 'illager_corsair',
        'illager_fort', 'illager_galley', 'illager_windmill', 'infested_temple', 'jungle_tree_house', 'keep_kayra',
        'kisegi_sanctuary', 'lighthouse', 'mechanical_nest', 'mining_complex', 'mining_system', 'monastery',
        'mushroom_house', 'mushroom_mines', 'mushroom_village', 'plague_asylum', 'scorched_mines', 'shiraz_palace',
        'thornborn_towers', 'typhon', 'undead_pirate_ship']] + [
        'nova_structures:illager_manor', 'nova_structures:lone_citadel', 'nova_structures:stray_fort',
        'nova_structures:toxic_lair', 'nova_structures:ruin_town', 'nova_structures:witch_villa'],
    'nether_dungeons': ['nova_structures:nether_keep', 'nova_structures:piglin_donjon', 'nova_structures:nether_port',
                        'nova_structures:piglin_outstation'],
    'end_dungeons': ['nova_structures:end_castle', 'nova_structures:end_lighthouse', 'nova_structures:end_ship'],
    # YUNG's Better Nether Fortresses / Better Strongholds replace (and turn off) the vanilla
    # structures, so "find a fortress / the stronghold" accepts both ids.
    'nether_fortresses': ['minecraft:fortress', 'betterfortresses:fortress'],
    'strongholds': ['minecraft:stronghold', 'betterstrongholds:stronghold'],
}


# Class buildings and their merchants in villages (each class mod's config/<mod>/villages.json
# adds the building to the vanilla village house pools; the merchant works there).
MERCHANTS = {
    'wizard': ['wizards:wizard_merchant'],        # Wizard Tower
    'sanctuary': ['paladins:monk'],               # Sanctuary
    'barracks': ['rogues:arms_merchant'],         # Barracks
    'range': ['archers:archery_artisan'],         # Archery Range
    'pub': ['bards_rpg:luthier'],                 # Bard's pub
}
MERCHANTS['any'] = [p for ps in MERCHANTS.values() for p in ps] + ['jewelry:jeweler']
MERCHANTS['jeweler'] = ['jewelry:jeweler']  # The Adventurer's Kit

# Explorer maps given by quest rewards (loot tables kubejs/data/minerpg/loot_table/map/<key>.json,
# run with /loot give, which searches from the player's position). Overworld targets only.
# key: (map name, structure tag the map searches for, extra tag contents or None if the tag exists)
MAPS = {
    'small_dungeon': ('Map to a Small Dungeon', 'minerpg:small_dungeons', None),
    # Given once on a player's first join (not by a quest).
    'tavern': ('Map to the Nearest Tavern', 'minerpg:taverns', None),
    'amethyst_nest': ('Map to the Amethyst Nest', 'minerpg:map/amethyst_nest', ['cataclysm:amethyst_nest']),
    'great_dungeon': ('Map to a Great Dungeon', 'minerpg:map/great_dungeon', ['dungeons_arise:' + n for n in [
        'abandoned_temple', 'bandit_towers', 'ceryneian_hind', 'coliseum', 'foundry', 'illager_fort', 'infested_temple',
        'jungle_tree_house', 'keep_kayra', 'kisegi_sanctuary', 'mechanical_nest', 'mining_complex', 'monastery',
        'mushroom_mines', 'plague_asylum', 'scorched_mines', 'shiraz_palace', 'thornborn_towers']] + [
        'nova_structures:illager_manor', 'nova_structures:lone_citadel', 'nova_structures:stray_fort',
        'nova_structures:toxic_lair', 'nova_structures:witch_villa']),
    'cursed_pyramid': ('Map to the Cursed Pyramid', 'minerpg:map/cursed_pyramid', ['cataclysm:cursed_pyramid']),
    'frosted_prison': ('Map to the Frosted Prison', 'minerpg:map/frosted_prison', ['cataclysm:frosted_prison']),
    'sunken_city': ('Map to the Sunken City', 'minerpg:map/sunken_city', ['cataclysm:sunken_city']),
    'ancient_city': ('Map to an Ancient City', 'minerpg:map/ancient_city', ['minecraft:ancient_city']),
    'ancient_factory': ('Map to the Ancient Factory', 'minerpg:map/ancient_factory', ['cataclysm:ancient_factory']),
    'stronghold': ('Map to the Stronghold', 'minerpg:strongholds', None),
    # Explorer Survey Maps (used up into these by kubejs/server_scripts/minerpg_jobs.js).
    'survey_settlement': ('Survey Map: Nearest Settlement', 'minerpg:map/survey_settlement',
                          ['#minecraft:village'] + [f'nova_structures:tavern_{w}' for w in TAVERN_WOODS]),
    'survey_crypt': ('Survey Map: Nearest Crypt', 'minerpg:small_dungeons', None),
    'survey_dungeon': ('Survey Map: Nearest Great Dungeon', 'minerpg:map/great_dungeon', None),
    'survey_lair': ('Survey Map: Nearest Boss Lair', 'minerpg:map/survey_lair', [
        'cataclysm:amethyst_nest', 'cataclysm:cursed_pyramid', 'cataclysm:frosted_prison', 'cataclysm:sunken_city',
        'cataclysm:ancient_factory', 'mowziesmobs:wrought_chamber', 'mowziesmobs:umvuthana_grove',
        'mowziesmobs:frostmaw_spawn']),
}


def r_map(key):
    return r_cmd(f'/loot give @s loot minerpg:map/{key}', MAPS[key][0])


def write_maps():
    folder = os.path.join(DATA, 'minerpg', 'loot_table', 'map')
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    for key, (name, tag, _ids) in MAPS.items():
        write(os.path.join(folder, key + '.json'), json.dumps({
            'type': 'minecraft:chest',
            'pools': [{'rolls': 1, 'entries': [{'type': 'minecraft:item', 'name': 'minecraft:map', 'functions': [
                # skip_existing_chunks false: also find a dungeon in chunks someone already loaded.
                {'function': 'minecraft:exploration_map', 'destination': tag, 'decoration': 'minecraft:red_x',
                 'zoom': 2, 'search_radius': 50, 'skip_existing_chunks': False},
                {'function': 'minecraft:set_name', 'target': 'item_name', 'name': {'text': name}},
            ]}]}],
        }, indent=2))


def write_structure_tags():
    folder = os.path.join(DATA, 'minerpg', 'tags', 'worldgen', 'structure')
    # Only this folder's top-level files are generated. Subfolders (dungeon_tier/: the Dungeon
    # Difficulty tier tags read by config/dungeon_difficulty/difficulty_v2.json) are hand-written.
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if name.endswith('.json'):
                os.remove(os.path.join(folder, name))
    if os.path.isdir(os.path.join(folder, 'map')):
        shutil.rmtree(os.path.join(folder, 'map'))
    tags = dict(STRUCTURE_TAGS)
    for key, (_name, tag, ids) in MAPS.items():
        if ids:
            tags[tag.split(':', 1)[1]] = ids
    for name, ids in tags.items():
        # required: false so a missing mod never breaks the tag.
        write(os.path.join(folder, name + '.json'),
              json.dumps({'values': [{'id': i, 'required': False} for i in ids]}, indent=2))


# --------------------------------------------------------------------------------------
# "Has an item" tasks (hidden helper advancements, written by write_advancements)
# --------------------------------------------------------------------------------------
# path -> criteria/requirements. Filled while the quest tables below are defined, written later
# (write_advancements wipes and rewrites the folders first).
HAS_ADV = {}


def has_any(path, items, title):
    """Task: the player has any one of `items` (ids, or a single '#tag') anywhere in the inventory."""
    HAS_ADV[path] = ({'has': {'trigger': 'minecraft:inventory_changed', 'conditions': {'items': [{'items': items}]}}}, False)
    return t_adv('minerpg:' + path, title)


def has_sets(path, sets, title):
    """Task: the player has all pieces of at least one of `sets` (lists of ids) at the same time.
    Worn armor counts: the armor slots are part of the inventory."""
    criteria = {f'set_{i}': {'trigger': 'minecraft:inventory_changed', 'conditions': {
        'items': [{'items': [piece]} for piece in pieces]}} for i, pieces in enumerate(sets)}
    HAS_ADV[path] = (criteria, len(sets) > 1)
    return t_adv('minerpg:' + path, title)


# --------------------------------------------------------------------------------------
# Quest book content
# --------------------------------------------------------------------------------------
# A quest: key, title, x, y, description lines, tasks, rewards, deps (keys), extra fields.
def Q(key, title, x, y, desc, tasks, rewards=(), deps=(), subtitle=None, **extra):
    return dict(key=key, title=title, x=x, y=y, desc=desc, tasks=list(tasks), rewards=list(rewards),
                deps=list(deps), subtitle=subtitle, extra=extra)


KIT_TABLE = 'class_kits'

GETTING_STARTED = [
    Q('gs_welcome', 'Welcome, Traveler', 0, 0, [
        'This book walks with you from your first night to the edge of the world.',
        'Each tab is a chapter. Each quest points at something worth trying, and pays you for it.',
        '',
        'Press L whenever you are lost.',
        'Your &6Adventurer\'s Handbook&r knows how this world works: races, classes, jobs, zones, loot, parties, and a Field Guide that fills in as you explore. Lost it? A book and a feather make another.',
        '',
        'Tick the box to begin.'],
        [t_check('Open the book')],
        # Sets the Apotheosis world tier to Haven (or higher, if already unlocked), which also
        # ends the "unknown power" tutorial on affix items. No handbook here: every player gets one on first join
        # (kubejs/server_scripts/minerpg_first_join.js), and a book and a feather craft another. (Rewards keep their
        # ids by position, so dropping the last one leaves the others intact.)
        [r_item('minecraft:bread', 8), r_cmd('/function minerpg:tier/sync')], subtitle='Start here'),
    Q('gs_race', 'Who Are You?', -2, -1.5, [
        'Your folk gave you a few small gifts, one drawback and one power.',
        '',
        'Use your racial power once. V, unless you changed it.'],
        [t_check('Use your racial power')], [r_xp(30)], deps=['gs_welcome'], subtitle='Your race and its power'),
    Q('gs_calling', 'Choose Your Calling', 2, 0, [
        'Choose who you start as. You get the class tome, a starter weapon, one armor piece, and the runes or arrows it burns.',
        '',
        'Nothing is final: a second class waits at any Spell Binding Table.',
        '',
        'Your class\'s road from here, weapon by weapon and set by set, opens in the &6Your Calling&r tab.'],
        [t_check('I am ready to choose')], [{'type': 'choice', '_table': KIT_TABLE}, r_item('minecraft:emerald', 6)],
        deps=['gs_welcome'], subtitle='Your class starter kit', size=Double(1.5), shape='hexagon'),
    Q('gs_cast', 'Bound to the Book', 4, -1.5, [
        'Tome in its spell book slot. A weapon of the same class in hand.',
        'Now cast: the spell keys are shown on your hotbar.'],
        [t_adv('cast', 'Cast any spell')], [r_xp(30)], deps=['gs_calling'], subtitle='Equip your tome, cast a spell'),
    Q('gs_runes', 'Stones That Remember', 6, -3, [
        'Many spells burn runes. Make them at a Rune Crafting Altar: same materials, more runes than a crafting table.'],
        [t_adv('runes', 'Craft any rune')], [r_item('runes:small_rune_pouch')], deps=['gs_cast'], subtitle='Craft runes'),
    Q('gs_binding', 'The Binding Table', 6, 0, [
        'Stronger spells are bound at a Spell Binding Table. Every plains village, yours included, keeps one in its gazebo. Or build your own and ring it with bookshelves.',
        'Put your tome in and pay in experience levels.'],
        [t_adv('bind', 'Bind a spell')], [r_item('minecraft:lapis_lazuli', 16), r_xp(40)], deps=['gs_cast'], subtitle='Learn new spells'),
    Q('gs_talent', 'A Point to Spend', 4, 1.5, [
        'Every kill teaches you something. Press N and spend your first talent point.',
        'Friends within 200 blocks learn from your kills too.',
        'Kills earn up to 9 points. The last 4 come from the great chapter bosses.'],
        [t_adv('talent', 'Unlock a talent')], [r_xp(30)], deps=['gs_calling'], subtitle='Spend a talent point'),
    Q('gs_roll', 'Light on Your Feet', -2, 1.5, [
        'Never take a blow you can roll away from. R, unless you changed it.',
        'Mid-roll, nothing can touch you. Rolls recharge over time.'],
        [t_check('Do a combat roll')], [r_item('minecraft:cooked_beef', 8)], deps=['gs_welcome'], subtitle='Dodge roll'),
    Q('gs_stats', 'Know Thyself', -4, 1.5, [
        'Open your inventory and press the sword button: spell power, crit, armor, all of it.'],
        [t_check('Open the stats screen')], [r_xp(20)], deps=['gs_roll'], subtitle='Your stats screen'),
    Q('gs_waystone', 'Stones of Passage', -2, 3, [
        'Waystones stand in villages and along the roads. Wake one, and any other waystone can bring you back to it.',
        'Each trip costs a little experience: farther costs more.'],
        [t_adv('waystone', 'Activate a waystone')], [r_item('waystones:warp_scroll', 3)], deps=['gs_welcome'], subtitle='Fast travel'),
    Q('gs_lootr', 'Yours Alone', 0, 3, [
        'Dungeon chests keep a share for each of you. No need to race your friends to the loot.'],
        [t_adv('lootr:1chest', 'Open a dungeon chest')], [r_xp(30)], deps=['gs_welcome'], subtitle='Personal dungeon chests'),
    Q('gs_rarity', 'Not All Blades Are Equal', 2, 3, [
        'Gear comes in rarities, each with its own color: Common, Uncommon, Rare, Epic, Mythic. The rarer, the more bonus stats.',
        'Gear you do not need goes to a Salvaging Table. Its scraps pay for reforging.',
        '',
        'Your &eworld tier&r (Ctrl+T to look) sets how tough monsters are and how good the loot is. It starts at Haven and climbs on its own as chapter bosses fall: Venture, Ascent, Summit, Pinnacle. It never goes back.'],
        [t_item('apotheosis:mysterious_scrap_metal', title='Salvage a piece of gear')], [r_item('apotheosis:gem_dust', 8)],
        deps=['gs_lootr'], subtitle='Gear rarity and salvaging'),
    Q('gs_locks', 'Locked Doors', 0, -3, [
        'You can walk anywhere. Two doors need keys:',
        '- &6Nether Sigil&r: from The Harbinger, at the end of the Overworld chapter. Fire will not wake a Nether portal; the sigil will.',
        '- &dVoid Shard&r: from Ignis, at the end of the Nether chapter. No Eye of Ender without one.',
        'Everyone near a boss when it falls gets their own key.'],
        [t_check('Understood')], [r_xp(20)], deps=['gs_welcome'], subtitle='The Nether Sigil and the Void Shard', shape='diamond'),
    Q('gs_party', 'Better Together', 2, -3, [
        'Press H for the Party HUD: invite your friends and keep their health in sight.',
        'Your spells and swings never hurt each other, and kills near a friend teach you both. Heals and buffs reach every player, party or not.',
        'In the Members tab, right-click each friend and add them to favorites to see their health frames.',
        'Every boss is built for a full party of four. Alone, you will not win. Bring your friends.',
        'Your quest book stays your own. When a boss falls, everyone nearby gets their own trophy or key.'],
        [t_check('Join or form a party')], [r_xp(30)], deps=['gs_welcome'], subtitle='Party HUD (H)'),
    Q('gs_jobs', 'Pick Your Trades', -6, 0, [
        'Press J and join two jobs. Each grows from its own work and pays a &6Gold Coin&r every level.',
        'Two jobs is the most anyone can hold. To swap one, type &e/leavejob <job>&r: it costs 5 gold and deletes that job\'s level and power-ups for good. Buy power-ups in the same menu with the &6coins&r you carry. Coins also come from quests, chests and bosses.',
        'The quests below show one way into each job.'],
        [t_check('Join two jobs')], [r_xp(30), r_coins(3)], deps=['gs_welcome'], subtitle='Jobs menu (J)'),
    Q('gs_job_gates', 'Masters of a Trade', -13.5, 0, [
        'Some things only a trained hand can &omake&r:',
        'Class gear is made by three trades, by tier: anyone can make tier 1; diamond tier 2 needs level 10, netherite tier 3 20, Armory sets 25.',
        '- &cSmith&r: plate armor and melee weapons (Warrior, Paladin, Berserker, Forcemaster). Reforging to Rare needs Smith 10, Epic 20, Mythic 30.',
        '- &2Hunter&r: leather armor, bows, crossbows, spears and quivers (Archer, Rogue).',
        '- &dEnchanter&r: robes, staves, wands and instruments (Wizard, mages, Priest, Bard), and the stronger enchanting shelves: Hellshelf and Seashelf at 10, their upgrades at 20, deep and sculk shelves at 25, endshelves at 30.',
        '- &5Alchemist&r: Strong and Long potions at 10, Splash at 15, Lingering at 20.',
        '- &3Jeweler&r: gold and gem jewelry at 10, Socket Mounts at 15, diamond and emerald jewelry at 20, netherite jewelry at 25.',
        '- &6Cook&r: plated meals at 10 (steak and potatoes, roasted mutton chops, grilled salmon, bacon and eggs, stuffed potato), feasts at 20. Cooking pot meals are free for everyone.',
        '- &9Explorer&r: Return, Warp and Portal Scrolls and Crypt Survey Maps at 10, Warp Stones and Sharestones at 15, Waystones, Portstones and Great Dungeon Survey Maps at 20, Warp Plates at 25, Boss Lair Survey Maps at 30. Waystones you find stay free to use.',
        '',
        'Anyone can &ouse&r these things. Class gear still drops from dungeons and bosses, class merchants sell it, plain bookshelves work for everyone, the Jeweler villager sells rings and necklaces, and a friend with the job can make it for you.',
        'Hover over an item to see the job and level that make it.',
        'Job experience also comes from the adventure: Smiths from reforging and salvaging, Enchanters from binding spells, Jewelers from cutting gems and setting them into gear, Alchemists from runes and potion charms, Hunters from skinning their kills and working leather, Cooks from every meal, Explorers from each new waystone they use.',
        'Class merchants buy crafted goods for emeralds: runes, diamond-tier class weapons and pot meals.'],
        [t_check('Understood')], [r_coins(1)], deps=['gs_jobs'], subtitle='Crafting gates and job experience', shape='diamond', optional=True),
    # v0.4 additions. Item rewards only, so Getting Started quest points stay as tuned.
    Q('gs_revive', 'Pick Them Up', 4, -3, [
        'With other players online, a killing blow leaves you &cdowned&r instead. You have 60 seconds.',
        'A friend holds use (right-click) on you for 3 seconds to pick you up. Heal spells cannot reach the downed: someone has to come to you.',
        'You get up with 3 hearts and a short Weakness. Fall again soon and the same timer keeps running.',
        'Alone on the server, nobody is coming: you simply die. Lava and the void kill at once.',
        'A real death costs you nothing: your things and experience wait in a &6grave&r where you fell. Chat tells you where.'],
        [t_check('Understood')], [r_item('minecraft:golden_apple', 1)], deps=['gs_party'], subtitle='Downed and revived', shape='diamond'),
    Q('gs_cooking', 'A Feast for the Party', -4, -3, [
        'Build a &6Cooking Pot&r and set it on a campfire or stove. Pot meals feed more and give the whole group buffs:',
        '- &aNourishment&r: your hunger stops dropping for a while.',
        '- &aComfort&r: you keep healing however hungry you are.',
        'Wild cabbages, tomatoes, onions and rice grow out in the world: break them for seeds. Hover over any food to see how much it restores.',
        'Anyone can cook in the pot. A &6Cook&r (J) earns job experience for it, and sometimes gets a second helping.'],
        [t_item('farmersdelight:cooking_pot', title='Craft a Cooking Pot')], [r_item('farmersdelight:tomato_seeds', 4), r_item('farmersdelight:cabbage_seeds', 4)],
        deps=['gs_welcome'], subtitle='Cooking (Farmer\'s Delight)'),
    # v0.5 village tour: the class buildings and merchants of your starting village.
    Q('gs_tour', 'Merchants of Every Calling', 4, 3, [
        'You start in a plains village. Besides its gazebo, villages can have buildings for the classes, each with its own merchant:',
        '- &dWizard Tower&r: Wizard Merchant (wizards and mages)',
        '- &eSanctuary&r: Monk (paladins and priests)',
        '- &cBarracks&r: Arms Dealer (rogues and warriors)',
        '- &aArchery Range&r: Archery Artisan (archers)',
        '- &6Pub&r: Luthier (bards)',
        'A Jeweler sells rings and necklaces. Not every village has every building: if yours lacks one, the next village may have it.',
        'Berserkers and forcemasters have no building of their own; the Arms Dealer and Jeweler serve everyone.',
        '',
        'Trade once with any of these merchants. Use the emeralds from your calling.'],
        [t_adv('trade_any', 'Trade with a class merchant')], [r_item('minecraft:emerald', 4)],
        deps=['gs_calling'], subtitle='Visit the village', optional=True),
]

# One optional quest per class building (personal books: do the one for your class).
TOUR = [
    ('wizard', 'The Wizard Tower', 'A tall tower of stone and purple glass. The Wizard Merchant sells staves, wands, robes and runes for Arcane, Fire and Frost Wizards (and mages can buy runes there too).', 'wizards:wand_arcane'),
    ('sanctuary', 'The Sanctuary', 'A small white chapel. The Monk sells holy weapons, armor and healing runes for Paladins and Priests.', 'paladins:holy_wand'),
    ('barracks', 'The Barracks', 'A guard house with weapon racks. The Arms Dealer sells daggers, sickles, axes and armor for Rogues and Warriors.', 'rogues:iron_dagger'),
    ('range', 'The Archery Range', 'Targets in a fenced yard. The Archery Artisan sells bows, crossbows, arrows and archer armor.', 'archers:composite_longbow'),
    ('pub', 'The Bard\'s Pub', 'A lively pub. The Luthier sells lutes and other instruments for Bards.', 'bards_rpg:wooden_lute'),
]
for i, (key, title, text, icon) in enumerate(TOUR):
    GETTING_STARTED.append(Q(f'gs_tour_{key}', title, 1 + i * 1.5, 4.5, [text, '', 'Find the building in a village and trade once with its merchant.'],
                             [t_adv(f'trade_{key}', 'Trade with the merchant')], [r_item('minecraft:emerald', 3)],
                             deps=['gs_tour'], subtitle='Class building', shape='circle', optional=True, icon={'id': icon}))

# Cooking pot meals (Farmer's Delight); any one completes the Cook starter.
POT_MEALS = ['farmersdelight:' + m for m in [
    'beef_stew', 'chicken_soup', 'vegetable_soup', 'fish_stew', 'pumpkin_soup', 'baked_cod_stew', 'noodle_soup',
    'bone_broth', 'onion_soup', 'mushroom_rice', 'fried_rice', 'cabbage_rolls', 'pasta_with_meatballs',
    'pasta_with_mutton_chop', 'vegetable_noodles', 'ratatouille', 'squid_ink_pasta', 'dumplings', 'tomato_sauce',
    'hot_cocoa', 'apple_cider', 'glow_berry_custard', 'cooked_rice', 'stuffed_pumpkin_block']]

JOB_STARTERS = [
    ('alchemist', 'Alchemist', 'Alchemists earn experience brewing, crafting runes and potion charms. Brew any potion.', t_adv('alchemist', 'Brew a potion'), r_item('minecraft:glass_bottle', 6)),
    ('enchanter', 'Enchanter', 'Enchanters earn experience at the enchanting table and the Spell Binding Table. Enchant any item.', t_adv('minecraft:story/enchant_item', 'Enchant an item'), r_item('minecraft:lapis_lazuli', 12)),
    ('cook', 'Cook', 'Cooks earn experience for every meal: stews and soups from the cooking pot, plated meals and feasts at the table. Plated meals need Cook 10, feasts Cook 20. Cook any meal in a cooking pot.',
     has_any('guide/pot_meal', POT_MEALS, 'Cook a pot meal'), r_item('minecraft:bowl', 8)),
    ('explorer', 'Explorer', 'Explorers draw Survey Maps that lead the party to settlements, crypts, dungeons and boss lairs, and build the waystone network. They also earn experience the first time they use each waystone. Draw a Survey Map from a map and an emerald.',
     t_item('minerpg:survey_map_settlement', title='Draw a Survey Map'), r_item('minecraft:map', 3)),
    ('farmer', 'Farmer', 'Farmers earn experience harvesting grown crops and raising animals. Bring in 16 wheat.', t_item('minecraft:wheat', 16), r_item('minecraft:bone_meal', 16)),
    ('hunter', 'Hunter', 'Hunters are skinners and leatherworkers. They earn experience for every hide, bone and monster part their kills drop (and find more of them as they level), for hunting animals and for crafting leather goods. Bring in 8 leather.', t_item('minecraft:leather', 8), r_item('minecraft:arrow', 32)),
    ('jeweler', 'Jeweler', 'Jewelers craft rings and necklaces, cut gems at the Jeweler\'s Kit and the Gem Cutting Table, and set gems into gear. Gold and gem jewelry needs Jeweler 10. Craft a Jeweler\'s Kit.', t_item('jewelry:jewelers_kit', title='Craft a Jeweler\'s Kit'), r_item('minecraft:gold_ingot', 6)),
    ('miner', 'Miner', 'Miners earn experience breaking stone and ores. Mine 16 coal.', t_item('minecraft:coal', 16), r_item('minecraft:torch', 32)),
    ('smith', 'Smith', 'Smiths earn experience smelting ingots, crafting tools, weapons and armor, and reforging and salvaging gear. Craft an iron pickaxe.', t_adv('minecraft:story/iron_tools', 'Craft an iron pickaxe'), r_item('minecraft:iron_ingot', 6)),
]
for i, (key, title, text, task, reward) in enumerate(JOB_STARTERS):
    col, row = i % 5, i // 5
    GETTING_STARTED.append(Q(f'gs_job_{key}', title, -12 + col * 1.5, -1.5 + row * 3, [text], [task], [reward, r_xp(10), r_coins(1)],
                             deps=['gs_jobs'], subtitle='Job starter', shape='circle'))


CHAPTER_1 = [
    # Hearthlands
    Q('c1_village', 'The Hearth Road', 0, 0, [
        'The &aHearthlands&r are the gentle lands: plains, forests, meadows and rivers, with villages, taverns and small dungeons. Learn your class here.',
        'Walk the streets of a village to begin.',
        '',
        '&7Reward: a map marking the nearest small dungeon.&r'],
        [t_struct('#minecraft:village', 'Visit a village')], [r_item('minecraft:emerald', 6), r_map('small_dungeon')], subtitle='Hearthlands'),
    Q('c1_tavern', 'A Warm Hearth', 1.5, -1.5, [
        'Taverns sit along the roads of the Hearthlands. Travelers trade, rest and swap stories there.',
        'The map you woke with leads to the nearest one.'],
        [t_struct('#minerpg:taverns', 'Visit a tavern')], [r_item('minecraft:cooked_porkchop', 8), r_xp(50)], deps=['c1_village'], subtitle='Hearthlands'),
    Q('c1_cellar', 'Cellar Dwellers', 1.5, 1.5, [
        'Something has nested under the fields. Find a small dungeon and clear out what lives there.',
        '',
        '&7Reward: a map marking the Amethyst Nest.&r'],
        [t_struct('#minerpg:small_dungeons', 'Find a small dungeon'), t_kill(count=15, tag='minecraft:undead', title='Kill 15 undead')],
        [r_xp(75), r_item('minecraft:iron_ingot', 8), r_map('amethyst_nest')], deps=['c1_village'], subtitle='Hearthlands'),
    Q('c1_nest', 'Glitter in the Deep', 3, 0, [
        'Deep in the lush caves, an amethyst nest glows. Its keeper does not like visitors.'],
        [t_struct('cataclysm:amethyst_nest', 'Find the Amethyst Nest')], [r_xp(75)], deps=['c1_cellar'], subtitle='Hearthlands'),
    Q('c1_crab', 'Shell Shock', 4.5, 0, [
        'Defeat the &dAmethyst Crab&r. Everyone nearby at the kill earns a Geode Claw for this quest.',
        'The claw raises your world tier to &eVenture&r: monsters wear more armor, rare monsters start to roam, and gear drops in iron and better rarities.',
        '',
        '&7Reward: a map marking a great dungeon of the Wildlands.&r'],
        [t_item('minerpg:trophy_amethyst_crab', title='Geode Claw')], [r_item('minecraft:diamond', 3), r_xp(150), r_map('great_dungeon')],
        deps=['c1_nest'], subtitle='Boss', shape='gear', size=Double(1.5)),
    Q('c1_iron', 'Ironclad', 3, 2.5, [
        'Good iron makes good gear. Stock up for your first upgrades.'],
        [t_item('minecraft:iron_ingot', 24)], [r_item('minecraft:chainmail_chestplate'), r_xp(50)], deps=['c1_village'], subtitle='Side task'),
    Q('c1_waystone', 'A Stone of Your Own', 0, 2.5, [
        'Craft a waystone and set it at your home.',
        'The Warp Stone you earn here takes you to any waystone you know, from anywhere, for free. It needs 5 minutes to recover after each use.'],
        [t_item('waystones:waystone')], [r_item('waystones:warp_stone')], deps=['c1_village'], subtitle='Side task'),
    Q('c1_wroughtnaut', 'The Iron Sentinel', 4.5, 2.5, [
        'Deep under the Hearthlands, a sealed chamber holds a suit of armor that is not empty: the &7Ferrous Wroughtnaut&r.',
        'Its armor turns most blows. Dodge the axe, then strike its back while it recovers.',
        'Optional. Everyone nearby at the kill earns a Wrought Rivet.'],
        [t_item('minerpg:trophy_ferrous_wroughtnaut', title='Wrought Rivet')], [r_item('minecraft:iron_block', 2), r_xp(75)],
        deps=['c1_cellar'], subtitle='Optional boss', shape='gear', optional=True),
    # Wildlands
    Q('c1_wild', 'Into the Wildlands', 6.5, 0, [
        'The &6Wildlands&r are the harsh lands: deserts, jungles, swamps, taigas, dark forests and open sea. Big dungeons and ruins hide there, and monsters hit harder.',
        'Explore one of the great dungeons of the wild.'],
        [t_struct('#minerpg:wildlands_dungeons', 'Explore a great dungeon')], [r_xp(75)], deps=['c1_crab'], subtitle='Wildlands'),
    Q('c1_desert_eye', 'Eye of the Dunes', 8, -2.45, [
        'An Eye of Desert points the way to the cursed pyramid. Craft one and throw it.'],
        [t_item('cataclysm:desert_eye')], [r_xp(50)], deps=['c1_wild'], subtitle='Side task'),
    Q('c1_rumor_pyramid', 'Whispers of Sand', 8, -3.55, [
        'Caravan guards tell of a pyramid that swallows the sun. Ask around, and someone sketches you a map.',
        '',
        '&7Reward: a map marking the Cursed Pyramid.&r'],
        [t_check('Ask for directions')], [r_map('cursed_pyramid')], deps=['c1_wild'], subtitle='Map', shape='diamond', size=Double(0.75)),
    Q('c1_rumor_prison', 'Whispers of Ice', 8, -1.55, [
        'Trappers speak of black ice where nothing grows. One of them still has a map.',
        '',
        '&7Reward: a map marking the Frosted Prison.&r'],
        [t_check('Ask for directions')], [r_map('frosted_prison')], deps=['c1_wild'], subtitle='Map', shape='diamond', size=Double(0.75)),
    Q('c1_rumor_sunken', 'Whispers of the Tide', 8, 0.45, [
        'Fishermen avoid one stretch of sea: towers stand under the water there. They marked it for you.',
        '',
        '&7Reward: a map marking the Sunken City.&r'],
        [t_check('Ask for directions')], [r_map('sunken_city')], deps=['c1_wild'], subtitle='Map', shape='diamond', size=Double(0.75)),
    Q('c1_pyramid', 'The Cursed Pyramid', 9.5, -3, [
        'A pyramid half-buried in desert sand, its door sealed with old curses.'],
        [t_struct('cataclysm:cursed_pyramid', 'Find the Cursed Pyramid')], [r_xp(100)], deps=['c1_wild'], subtitle='Wildlands'),
    Q('c1_remnant', 'Bones of the Sun King', 11, -3, [
        'Defeat the &6Ancient Remnant&r in the depths of the pyramid.',
        '',
        '&7Reward: a map marking an ancient city of the Frontier.&r'],
        [t_item('minerpg:trophy_ancient_remnant', title='Sun-Bleached Fang')], [r_item('minecraft:diamond', 4), r_xp(150), r_map('ancient_city')],
        deps=['c1_pyramid'], subtitle='Boss', shape='gear', size=Double(1.5)),
    Q('c1_cursed_eye', 'Eye of the Frost', 8, -0.45, [
        'An Eye of Curse leads to a prison buried in snow. Craft one and throw it.'],
        [t_item('cataclysm:cursed_eye')], [r_xp(50)], deps=['c1_wild'], subtitle='Side task'),
    Q('c1_prison', 'The Frosted Prison', 9.5, -1, [
        'A fortress of black ice where something was locked away on purpose.'],
        [t_struct('cataclysm:frosted_prison', 'Find the Frosted Prison')], [r_xp(100)], deps=['c1_wild'], subtitle='Wildlands'),
    Q('c1_maledictus', 'The Cursed Warden', 11, -1, [
        'Defeat &bMaledictus&r, the prisoner who became the prison.',
        '',
        '&7Reward: a map marking an ancient city of the Frontier.&r'],
        [t_item('minerpg:trophy_maledictus', title='Frostbound Crown')], [r_item('minecraft:diamond', 4), r_xp(150), r_map('ancient_city')],
        deps=['c1_prison'], subtitle='Boss', shape='gear', size=Double(1.5)),
    Q('c1_abyss_eye', 'Eye of the Deep', 8, 1.55, [
        'An Eye of Abyss finds the sunken city. Craft one and throw it from a boat.'],
        [t_item('cataclysm:abyss_eye')], [r_xp(50)], deps=['c1_wild'], subtitle='Side task'),
    Q('c1_sunken', 'The Sunken City', 9.5, 1, [
        'Towers of blue stone under the waves. Bring water breathing.'],
        [t_struct('cataclysm:sunken_city', 'Find the Sunken City')], [r_item('minecraft:potion', 2, {'minecraft:potion_contents': {'potion': 'minecraft:long_water_breathing'}}), r_xp(100)],
        deps=['c1_wild'], subtitle='Wildlands'),
    Q('c1_leviathan', 'Teeth of the Tide', 11, 1, [
        'Defeat &9The Leviathan&r in its flooded hall. It is untouchable out of the water, so fight it in its element.',
        '',
        '&7Reward: a map marking an ancient city of the Frontier.&r'],
        [t_item('minerpg:trophy_leviathan', title='Abyssal Scale')], [r_item('minecraft:diamond', 4), r_xp(150), r_map('ancient_city')],
        deps=['c1_sunken'], subtitle='Boss', shape='gear', size=Double(1.5)),
    Q('c1_umvuthi', 'The Sunbird\'s Court', 6.5, -2.5, [
        'Masked Umvuthana guard a grove in the savanna. Their chief, &6Umvuthi, the Sunbird&r, calls down sunfire and heals behind his followers.',
        'Optional. Everyone nearby at the kill earns a Sunbird Plume.'],
        [t_item('minerpg:trophy_umvuthi', title='Sunbird Plume')], [r_item('minecraft:gold_block', 2), r_xp(100)],
        deps=['c1_wild'], subtitle='Optional boss', shape='gear', optional=True),
    Q('c1_frostmaw', 'Rimefang', 8, 3, [
        'Something huge sleeps in the snowfields and on the ice spikes: the &bFrostmaw&r. Wake it and it breathes ice.',
        'Optional. Everyone nearby at the kill earns a Rimefang Tusk.'],
        [t_item('minerpg:trophy_frostmaw', title='Rimefang Tusk')], [r_item('minecraft:diamond', 3), r_xp(100)],
        deps=['c1_wild'], subtitle='Optional boss', shape='gear', optional=True),
    Q('c1_diamonds', 'Glittering Hoard', 6.5, 2.5, [
        'Diamond gear is the next step. Bring back a handful.'],
        [t_item('minecraft:diamond', 8)], [r_item('runes:medium_rune_pouch'), r_xp(100)], deps=['c1_wild'], subtitle='Side task'),
    # Frontier
    Q('c1_frontier', 'The Frontier', 13, 0, [
        'The &cFrontier&r is the extreme: frozen peaks, ice spikes, the deep dark and the deep ocean. The hardest lands of this world.',
        'Beat at least one Wildlands boss, then find an ancient city in the deep dark.',
        '',
        '&7Reward: a map marking the Ancient Factory.&r'],
        [t_struct('minecraft:ancient_city', 'Find an ancient city')], [r_xp(100), r_map('ancient_factory')],
        deps=['c1_remnant', 'c1_maledictus', 'c1_leviathan'], subtitle='Frontier', dependency_requirement='one_completed'),
    Q('c1_echo', 'Echoes Below', 13, 2, [
        'The deep dark keeps its secrets in echo shards. Bring some back, quietly.'],
        [t_item('minecraft:echo_shard', 4)], [r_item('minecraft:experience_bottle', 16)], deps=['c1_frontier'], subtitle='Side task'),
    Q('c1_mech_eye', 'Eye of Iron', 14.5, -2, [
        'An Eye of Mech points to the ancient factory. Craft one and follow it.'],
        [t_item('cataclysm:mech_eye')], [r_xp(75)], deps=['c1_frontier'], subtitle='Side task'),
    Q('c1_factory', 'The Ancient Factory', 14.5, 0, [
        'Rusted halls under the mountains, still humming. Something there is still awake.'],
        [t_struct('cataclysm:ancient_factory', 'Find the Ancient Factory')], [r_xp(150)], deps=['c1_frontier'], subtitle='Frontier'),
    Q('c1_harbinger', 'The Harbinger', 16.5, 0, [
        'Defeat &4The Harbinger&r, the factory\'s iron herald.',
        'Everyone nearby at the kill receives a &6Nether Sigil&r: use it on an obsidian frame to open the way to the Nether.',
        'The sigil raises your world tier to &eAscent&r. Your reward includes netherite upgrade templates for the next tier and a talent point.'],
        [t_item('minerpg:nether_sigil', title='Nether Sigil')],
        [r_item('minecraft:netherite_upgrade_smithing_template', 2), r_item('minecraft:diamond', 6), r_xp(500), r_talent_point(), r_coins(5)],
        deps=['c1_factory'], subtitle='Chapter boss', shape='gear', size=Double(2.0)),
    # Jobs (optional).
    Q('c1_job_10', 'Journeyman', 0, 4.5, [
        'Reach &6level 10&r in any of your jobs.',
        'At level 10, Smiths, Hunters and Enchanters make tier 1 class gear of their kind, Enchanters also the Hellshelf and Seashelf, Jewelers gold and gem jewelry, Cooks plated meals, Explorers scrolls and Crypt Survey Maps, and Alchemists brew Strong and Long potions.',
        '&7Checked when the job levels up.&r'],
        [t_adv('job_level_10', 'Reach level 10 in a job')], [r_coins(5), r_item('minecraft:emerald', 4)],
        deps=['c1_village'], subtitle='Job milestone', shape='circle', optional=True),
    Q('c1_job_craft', 'Made for a Friend', 1.5, 4.5, [
        'Make something only a trained hand can make: class gear as a Smith, Hunter or Enchanter, an enchanting shelf as an Enchanter, gem jewelry or a Socket Mount as a Jeweler, a plated meal or a feast as a Cook, a scroll or a Survey Map as an Explorer, or a Strong, Long, Splash or Lingering potion as an Alchemist.',
        'Then hand it to a party member who could not make it. That is what trades are for.'],
        [t_adv('job_gated_craft', 'Make a job-gated item')], [r_coins(5), r_item('minecraft:emerald', 6)],
        deps=['c1_job_10'], subtitle='Job milestone', shape='circle', optional=True),
]

CHAPTER_2 = [
    Q('c2_arrive', 'Through the Veil', 0, 0, [
        'Light a portal with your Nether Sigil and step through. The Nether is hotter and meaner than anything above.',
        'Lost your portal? Inside the Nether, normal fire still lights one, so you can always get home.'],
        [t_dim('minecraft:the_nether', 'Enter the Nether')], [r_item('minecraft:potion', 2, {'minecraft:potion_contents': {'potion': 'minecraft:long_fire_resistance'}}), r_xp(200)],
        subtitle='Chapter start'),
    Q('c2_fortress', 'Fortress of Flame', 1.5, -1.5, [
        'Dark brick bridges cross the lava seas. Find a fortress.'],
        [t_struct('#minerpg:nether_fortresses', 'Find a Nether fortress')], [r_xp(200)], deps=['c2_arrive']),
    Q('c2_blaze', 'Burning Wardens', 3, -2.5, [
        'Blazes guard the fortress. Their rods feed brewing stands and Eyes of Ender alike.'],
        [t_kill('minecraft:blaze', 6), t_item('minecraft:blaze_rod', 6)], [r_item('minecraft:blaze_rod', 4), r_xp(200)], deps=['c2_fortress']),
    Q('c2_wart', 'Wart and All', 3, -0.5, [
        'Nether wart grows in fortress gardens. Every real potion starts with it.'],
        [t_item('minecraft:nether_wart', 16)], [r_item('minecraft:brewing_stand'), r_xp(150)], deps=['c2_fortress'], subtitle='Side task'),
    Q('c2_skulls', 'Grim Trophies', 4.5, -2.5, [
        'Wither skeletons roam the fortress halls. Their skulls are needed if you ever dare summon the Wither.'],
        [t_item('minecraft:wither_skeleton_skull', 1)], [r_xp(200)], deps=['c2_blaze'], subtitle='Side task'),
    Q('c2_bastion', 'Bastion of Gold', 1.5, 1.5, [
        'Piglins hoard gold in huge black fortresses. Find a bastion.'],
        [t_struct('minecraft:bastion_remnant', 'Find a bastion')], [r_xp(200)], deps=['c2_arrive']),
    Q('c2_brutes', 'Brute Force', 3, 1.5, [
        'Piglin brutes do not care about your gold. Show them what you learned up top.'],
        [t_kill('minecraft:piglin_brute', 3)], [r_item('minecraft:gold_block', 2), r_xp(200)], deps=['c2_bastion']),
    Q('c2_debris', 'Ancient Debris', 4.5, 1.5, [
        'Deep in the Nether, ancient debris resists even lava. Dig some up.'],
        [t_item('minecraft:ancient_debris', 4)], [r_item('minecraft:netherite_upgrade_smithing_template', 1), r_xp(300)], deps=['c2_bastion']),
    Q('c2_netherite', 'Netherite in Hand', 6, 1.5, [
        'Smelt the debris, mix it with gold and forge your first netherite ingot.'],
        [t_item('minecraft:netherite_ingot')], [r_xp(250)], deps=['c2_debris']),
    Q('c2_keep', 'Keep of Ash', 4.5, 3, [
        'Old keeps and piglin donjons dot the wastes. Explore one.'],
        [t_struct('#minerpg:nether_dungeons', 'Explore a Nether keep')], [r_item('minecraft:golden_apple', 2), r_xp(200)], deps=['c2_bastion'], subtitle='Side task'),
    Q('c2_monstrous_eye', 'Eye of Fury', 6, -1, [
        'An Eye of Monstrous leads to the soul blacksmith\'s forge. Craft one.'],
        [t_item('cataclysm:monstrous_eye')], [r_xp(150)], deps=['c2_fortress', 'c2_bastion'], dependency_requirement='one_completed', subtitle='Side task'),
    Q('c2_smith', 'The Soul Blacksmith', 7.5, 0, [
        'A forge built of blackstone and lava, guarded by its own creation.'],
        [t_struct('cataclysm:soul_black_smith', 'Find the Soul Blacksmith')], [r_xp(300)], deps=['c2_fortress', 'c2_bastion'], dependency_requirement='one_completed'),
    Q('c2_monstrosity', 'Forged in Fury', 9, 0, [
        'Defeat the &6Netherite Monstrosity&r. Beating it earns you a talent point.'],
        [t_item('minerpg:trophy_netherite_monstrosity', title='Molten Heart')], [r_item('minecraft:netherite_scrap', 4), r_xp(500), r_talent_point()],
        deps=['c2_smith'], subtitle='Boss', shape='gear', size=Double(1.5)),
    Q('c2_flame_eye', 'Eye of Flame', 10.5, -1.5, [
        'An Eye of Flame shows the way to the burning arena. Craft one.'],
        [t_item('cataclysm:flame_eye')], [r_xp(150)], deps=['c2_monstrosity'], subtitle='Side task'),
    Q('c2_arena', 'The Burning Arena', 10.5, 0, [
        'A ring of fire where a fallen knight still waits for challengers.'],
        [t_struct('cataclysm:burning_arena', 'Find the Burning Arena')], [r_xp(300)], deps=['c2_monstrosity']),
    Q('c2_ignis', 'Ignis', 12.5, 0, [
        'Defeat &cIgnis&r, the burning champion.',
        'Everyone nearby at the kill receives a &dVoid Shard&r. Eyes of Ender need it, and it is never used up.',
        'The shard raises your world tier to &eSummit&r. Your reward includes a talent point and a book of &bSpell Infinity&r: put it on your weapon at an anvil and your spells stop using runes.'],
        [t_item('minerpg:void_shard', title='Void Shard')],
        [r_item('minecraft:diamond_block', 1), r_item('minecraft:netherite_ingot', 1), r_xp(700), r_talent_point(),
         r_item('minecraft:enchanted_book', 1, SPELL_INFINITY_BOOK), r_coins(5)],
        deps=['c2_arena'], subtitle='Chapter boss', shape='gear', size=Double(2.0)),
    Q('c2_job_20', 'Expert', 0, 3, [
        'Reach &6level 20&r in any of your jobs.',
        'At level 20, Smiths, Hunters and Enchanters make diamond class gear; Smiths reforge to Epic, Enchanters make the upgraded hell and sea shelves, Jewelers diamond and emerald jewelry, Cooks feasts, Explorers waystones and Great Dungeon Survey Maps, and Alchemists brew Lingering potions.',
        '&7Checked when the job levels up.&r'],
        [t_adv('job_level_20', 'Reach level 20 in a job')], [r_coins(8), r_item('minecraft:emerald', 8)],
        deps=['c2_arrive'], subtitle='Job milestone', shape='circle', optional=True),
]

CHAPTER_3 = [
    Q('c3_eyes', 'Eyes of the Void', 0, 0, [
        'Craft Eyes of Ender from an ender pearl, blaze powder and your Void Shard. The shard stays in the grid.',
        'You need a dozen to wake an End portal (some frames already hold eyes).',
        '',
        '&7Reward: a map marking the nearest stronghold.&r'],
        [t_item('minecraft:ender_eye', 12)], [r_item('minecraft:ender_pearl', 4), r_xp(200), r_map('stronghold')], subtitle='Chapter start'),
    Q('c3_stronghold', 'The Stronghold', 1.5, 0, [
        'Throw an eye and follow it underground to the stronghold and its portal room.'],
        [t_struct('#minerpg:strongholds', 'Find the stronghold')], [r_xp(300)], deps=['c3_eyes']),
    Q('c3_end', 'Into the End', 3, 0, [
        'Fill the frame and jump in. There is no coming back until the dragon falls, or you die.'],
        [t_dim('minecraft:the_end', 'Enter the End')], [r_item('minecraft:golden_apple', 3)], deps=['c3_stronghold']),
    Q('c3_dragon', 'The Last Dragon', 4.5, 0, [
        'Destroy the crystals and slay the &5Ender Dragon&r. Everyone nearby earns a Dragonscale.',
        'With both the Dragonscale and the Citadel Keystone, your world tier rises to &ePinnacle&r.'],
        [t_item('minerpg:trophy_ender_dragon', title='Dragonscale')], [r_item('minecraft:netherite_ingot', 2), r_xp(1500)],
        deps=['c3_end'], subtitle='Boss', shape='gear', size=Double(2.0)),
    Q('c3_city', 'Cities Among the Stars', 6, -1.5, [
        'Past the outer islands stand purple cities. Take a gateway and find one.'],
        [t_struct('minecraft:end_city', 'Find an End city')], [r_xp(300)], deps=['c3_dragon']),
    Q('c3_shells', 'Shell Collector', 7.5, -2.5, [
        'Shulkers guard the cities. Their shells make portable chests.'],
        [t_item('minecraft:shulker_shell', 4)], [r_item('minecraft:ender_chest'), r_xp(200)], deps=['c3_city'], subtitle='Side task'),
    Q('c3_wings', 'Wings of the End', 7.5, -0.5, [
        'End ships carry a pair of wings. Claim them.'],
        [t_item('minecraft:elytra')], [r_item('minecraft:firework_rocket', 32)], deps=['c3_city'], subtitle='Side task'),
    Q('c3_castle', 'The Castle at the Edge', 6, 1.5, [
        'Some outer islands hold great castles and lighthouses. Explore one.'],
        [t_struct('#minerpg:end_dungeons', 'Explore an End castle or lighthouse')], [r_item('minecraft:diamond', 6), r_xp(300)], deps=['c3_dragon'], subtitle='Side task'),
    Q('c3_void_eye', 'Eye of the Void', 7.5, 1.5, [
        'An Eye of Void finds the ruined citadel. Craft one.'],
        [t_item('cataclysm:void_eye')], [r_xp(200)], deps=['c3_dragon'], subtitle='Side task'),
    Q('c3_citadel', 'The Ruined Citadel', 9, 0, [
        'A broken fortress drifting at the edge of the void.'],
        [t_struct('cataclysm:ruined_citadel', 'Find the Ruined Citadel')], [r_xp(400)], deps=['c3_dragon']),
    Q('c3_guardian', 'Guardian of the Void', 10.5, 0, [
        'Defeat the &5Ender Guardian&r, last warden of the citadel. Beating it earns you your last talent point.',
        'With both the Citadel Keystone and the Dragonscale, your world tier rises to &ePinnacle&r.'],
        [t_item('minerpg:trophy_ender_guardian', title='Citadel Keystone')], [r_item('minecraft:netherite_ingot', 2), r_item('minecraft:enchanted_golden_apple'), r_xp(1800), r_talent_point(), r_coins(5)],
        deps=['c3_citadel'], subtitle='Chapter boss', shape='gear', size=Double(2.0)),
    Q('c3_job_30', 'Master', 0, 2, [
        'Reach &6level 30&r in any of your jobs.',
        'At level 30, Smiths, Hunters and Enchanters make the Armory sets from Ignis\'s upgrade crystals; Smiths reforge to Mythic, Enchanters make endshelves and Explorers draw Survey Maps to boss lairs.',
        '&7Checked when the job levels up.&r'],
        [t_adv('job_level_30', 'Reach level 30 in a job')], [r_coins(12), r_item('minecraft:emerald_block', 2)],
        deps=['c3_eyes'], subtitle='Job milestone', shape='circle', optional=True),
    Q('c3_wither_call', 'Call of the Wither', 9, 3, [
        'Optional raid. Bring three wither skeleton skulls and soul sand, and pick a place you do not mind losing.'],
        [t_item('minecraft:wither_skeleton_skull', 3), t_item('minecraft:soul_sand', 4)], [r_item('minecraft:golden_apple', 4)],
        deps=['c3_dragon'], subtitle='Optional raid', optional=True),
    Q('c3_wither', 'The Wither', 10.5, 3, [
        'Summon and destroy &8the Wither&r with your whole group. Everyone nearby earns an Ashen Skull Shard.'],
        [t_item('minerpg:trophy_wither', title='Ashen Skull Shard')], [r_item('minecraft:beacon'), r_xp(800)],
        deps=['c3_wither_call'], subtitle='Optional raid', shape='gear', size=Double(1.5), optional=True),
]

def pieces(chest):
    """The four pieces of an armor set, from its chest piece id (every class set names them *_head/_chest/_legs/_feet)."""
    return [chest.replace('chest', slot) for slot in ('head', 'chest', 'legs', 'feet')]


# --------------------------------------------------------------------------------------
# Your Calling: one row per class kit, from the tome to the endgame set
# --------------------------------------------------------------------------------------
# Design: docs/superpowers/specs/2026-10-31-minerpg-calling-and-guides-design.md. A row stays hidden
# until the player has that class: advancement minerpg:calling/<kit>/start is granted by the kit
# function and by kubejs/server_scripts/minerpg_calling.js (written below) when a tome of that
# class sits in the inventory or the spell book slot.

# Crafting job by gear group (pack/tools/gen_jobs.py GEAR_GROUP_JOB) and the levels that open each tier.
JOB_NAME = {'smith': 'Smith', 'hunter': 'Hunter', 'enchanter': 'Enchanter'}

# Class buildings in villages and their merchants (see MERCHANTS).
SHOP = {
    'wizard': 'the Wizard Merchant in the Wizard Tower',
    'sanctuary': 'the Monk in the Sanctuary',
    'barracks': 'the Arms Dealer in the Barracks',
    'range': 'the Archery Artisan in the Archery Range',
    'pub': 'the Luthier in the Bard\'s pub',
}

# Tier-1 armor materials (from each set's recipe): the reward for the first weapon, toward the first set.
T1_MATS = {
    'robe': [('minecraft:white_wool', 8), ('minecraft:lapis_lazuli', 6)],
    'elemental': [('minecraft:white_wool', 8), ('minecraft:lapis_lazuli', 4)],
    'paladin': [('minecraft:iron_ingot', 8), ('minecraft:copper_ingot', 8)],
    'priest': [('minecraft:white_wool', 8), ('minecraft:chain', 4)],
    'rogue': [('minecraft:white_wool', 8), ('minecraft:leather', 8)],
    'warrior': [('minecraft:iron_ingot', 8), ('minecraft:leather', 6)],
    'wildling': [('minecraft:leather', 8), ('minecraft:chain', 4)],
    'oriene': [('minecraft:white_wool', 8), ('minecraft:leather', 8)],
    'archer': [('minecraft:leather', 8), ('minecraft:chain', 4)],
    'bard': [('minecraft:white_wool', 8), ('minecraft:leather', 6), ('minecraft:purple_dye', 2)],
}

WIZ = 'wizards'
ELE = 'elemental_wizards_rpg'
ARS = 'arsenal'


def school(school, armory):
    """Wizard school row data: weapons and robes named after the school."""
    return dict(
        weapons=([f'{WIZ}:staff_wizard'], [f'{WIZ}:wand_{school}', f'{WIZ}:staff_{school}'],
                 [f'{WIZ}:wand_netherite_{school}', f'{WIZ}:staff_netherite_{school}']),
        weapon_words=('a Wizard Staff', f'a {school.title()} Wand or Staff', f'a netherite {school.title()} Wand or Staff'),
        sets=(f'{WIZ}:wizard_robe_chest', f'{WIZ}:{school}_robe_chest', f'{WIZ}:netherite_{school}_robe_chest'),
        set_names=('Wizard Robes', f'{school.title()} Robes', f'Netherite {school.title()} Robes'),
        armory=armory, armor_job='enchanter', weapon_job='Enchanter', shop='wizard', mats='robe',
        legend=[f'{ARS}:unique_staff_damage_{n}' for n in ('1', '2', '3', '4', '5', '6', 'sw')], legend_words='staff')


def element(name, word, base, armory):
    return dict(
        weapons=([f'{ELE}:staff_elemental'], [f'{ELE}:wand_{name}', f'{ELE}:staff_{name}'],
                 [f'{ELE}:wand_netherite_{name}', f'{ELE}:staff_netherite_{name}']),
        weapon_words=('an Elemental Staff', f'a {word} Wand or Staff', f'a netherite {word} Wand or Staff'),
        sets=(f'{ELE}:elemental_chest', f'{ELE}:{base}_chest', f'{ELE}:netherite_{base}_chest'),
        set_names=('Elemental Apprentice Robes', f'{word} Robes', f'Netherite {word} Robes'),
        armory=armory, armor_job='enchanter', weapon_job='Enchanter', shop=None, mats='elemental',
        legend=[f'{ELE}:unique_staff_1'] + [f'{ARS}:unique_staff_damage_{n}' for n in ('1', '2', '3', '4', '5', '6', 'sw')],
        legend_words='staff')


def bows(t1):
    return ([t1], ['archers:royal_longbow', 'archers:mechanic_shortbow'], ['archers:netherite_longbow', 'archers:netherite_shortbow'])


# Armory entries: (set name, chest id, crystal name). Crystals drop from Ignis, the Ender Guardian,
# the Ender Dragon and the Wither (config/rpg_series/loot_equipment_v2.json).
CALLING = {
    'arcane_wizard': school('arcane', [('Astral Robes', 'armory_rpgs:astral_robe_chest', "Conqueror's Lost Crystal"),
                                             ('Tempest Robes', 'armory_rpgs:tempest_robe_chest', "Conqueror's Forgotten Crystal")]),
    'fire_wizard': school('fire', [('Scarlet Robes', 'armory_rpgs:scarlet_robe_chest', "Conqueror's Lost Crystal"),
                                         ('Smouldering Robes', 'armory_rpgs:smouldering_robe_chest', "Conqueror's Forgotten Crystal")]),
    'frost_wizard': school('frost', [('Glacier Robes', 'armory_rpgs:glacier_robe_chest', "Vanquisher's Lost Crystal"),
                                           ('Rimeweave Robes', 'armory_rpgs:rimeweave_robe_chest', "Vanquisher's Forgotten Crystal")]),
    'water_mage': element('aqua', 'Aqua', 'kelp', [('Ocean Robes', f'{ELE}:ocean_robe_chest', "Warden's Lost Crystal")]),
    'earth_mage': element('terra', 'Terra', 'dripstone', [('Mountain Robes', f'{ELE}:mountain_robe_chest', "Warden's Lost Crystal")]),
    'wind_mage': element('wind', 'Wind', 'wind', [('Hurricane Robes', f'{ELE}:hurricane_robe_chest', "Warden's Lost Crystal")]),
    'paladin': dict(
        weapons=(['paladins:iron_claymore', 'paladins:iron_great_hammer', 'paladins:iron_mace'],
                 ['paladins:diamond_claymore', 'paladins:diamond_great_hammer', 'paladins:diamond_mace'],
                 ['paladins:netherite_claymore', 'paladins:netherite_great_hammer', 'paladins:netherite_mace']),
        weapon_words=('an iron Claymore, Great Hammer or Mace', 'a diamond Claymore, Great Hammer or Mace',
                      'a netherite Claymore, Great Hammer or Mace'),
        sets=('paladins:paladin_armor_chest', 'paladins:crusader_armor_chest', 'paladins:netherite_crusader_armor_chest'),
        set_names=('Paladin Armor', 'Crusader Armor', 'Netherite Crusader Armor'),
        armory=[('Justicar Armor', 'armory_rpgs:justicar_armor_chest', "Redeemer's Lost Crystal"),
                ('Lightbringer Armor', 'armory_rpgs:lightbringer_armor_chest', "Redeemer's Forgotten Crystal")],
        armor_job='smith', weapon_job='Smith', shop='sanctuary', mats='paladin',
        legend=[f'{ARS}:unique_{t}_{n}' for t in ('claymore', 'hammer', 'mace') for n in ('1', '2', 'sw')],
        legend_words='claymore, hammer or mace'),
    'priest': dict(
        weapons=(['paladins:holy_wand', 'paladins:holy_staff'], ['paladins:diamond_holy_wand', 'paladins:diamond_holy_staff'],
                 ['paladins:netherite_holy_wand', 'paladins:netherite_holy_staff']),
        weapon_words=('a Holy Wand or Holy Staff', 'a diamond Holy Wand or Staff', 'a netherite Holy Wand or Staff'),
        sets=('paladins:priest_robe_chest', 'paladins:prior_robe_chest', 'paladins:netherite_prior_robe_chest'),
        set_names=('Priest Vestments', 'Prior Vestments', 'Netherite Prior Vestments'),
        armory=[('Avatar Vestments', 'armory_rpgs:avatar_robe_chest', "Redeemer's Lost Crystal"),
                ('Absolution Vestments', 'armory_rpgs:absolution_robe_chest', "Redeemer's Forgotten Crystal")],
        armor_job='enchanter', weapon_job='Enchanter', shop='sanctuary', mats='priest',
        legend=[f'{ARS}:unique_staff_heal_{n}' for n in ('1', '2', 'sw')], legend_words='healing staff'),
    'rogue': dict(
        weapons=(['rogues:iron_dagger', 'rogues:iron_sickle'], ['rogues:diamond_dagger', 'rogues:diamond_sickle'],
                 ['rogues:netherite_dagger', 'rogues:netherite_sickle']),
        weapon_words=('an iron Dagger or Sickle', 'a diamond Dagger or Sickle', 'a netherite Dagger or Sickle'),
        sets=('rogues:rogue_armor_chest', 'rogues:assassin_armor_chest', 'rogues:netherite_assassin_armor_chest'),
        set_names=('Rogue Armor', 'Assassin Armor', 'Netherite Assassin Armor'),
        armory=[('Deathmantle Armor', 'armory_rpgs:deathmantle_armor_chest', "Champion's Lost Crystal"),
                ('Slayer Armor', 'armory_rpgs:slayer_armor_chest', "Champion's Forgotten Crystal")],
        armor_job='hunter', weapon_job='Hunter', shop='barracks', mats='rogue',
        legend=[f'{ARS}:unique_{t}_{n}' for t in ('dagger', 'sickle') for n in ('1', '2', 'sw')], legend_words='dagger or sickle'),
    'warrior': dict(
        weapons=(['rogues:iron_double_axe', 'rogues:iron_glaive'], ['rogues:diamond_double_axe', 'rogues:diamond_glaive'],
                 ['rogues:netherite_double_axe', 'rogues:netherite_glaive']),
        weapon_words=('an iron Double Axe or Glaive', 'a diamond Double Axe or Glaive', 'a netherite Double Axe or Glaive'),
        sets=('rogues:warrior_armor_chest', 'rogues:berserker_armor_chest', 'rogues:netherite_berserker_armor_chest'),
        set_names=('Warrior Armor', 'Berserker Armor', 'Netherite Berserker Armor'),
        armory=[('Destroyer Armor', 'armory_rpgs:destroyer_armor_chest', "Champion's Lost Crystal"),
                ('Onslaught Armor', 'armory_rpgs:onslaught_armor_chest', "Champion's Forgotten Crystal")],
        armor_job='smith', weapon_job='Smith', shop='barracks', mats='warrior',
        legend=[f'{ARS}:unique_{t}_{n}' for t in ('double_axe', 'glaive') for n in ('1', '2', 'sw')] + [f'{ARS}:unique_longsword_sw'],
        legend_words='axe, glaive or longsword'),
    'berserker': dict(
        weapons=(['berserker_rpg:iron_berserker_axe'], ['berserker_rpg:diamond_berserker_axe'], ['berserker_rpg:netherite_berserker_axe']),
        weapon_words=('an iron Berserker Axe', 'a diamond Berserker Axe', 'a netherite Berserker Axe'),
        sets=('berserker_rpg:wildling_chest', 'berserker_rpg:northling_chest', 'berserker_rpg:netherite_northling_chest'),
        set_names=('Wildling Suit', 'Northling Suit', 'Netherite Northling Suit'),
        armory=[('Norse Warlord Suit', 'berserker_rpg:warlord_chest', "Ravager's Lost Crystal")],
        armor_job='smith', weapon_job='Smith', shop=None, mats='wildling',
        legend=['berserker_rpg:unique_berserker_axe_1', 'berserker_rpg:unique_berserker_axe_2', 'berserker_rpg:unique_sword_1'],
        legend_words='axe or sword'),
    'forcemaster': dict(
        weapons=(['forcemaster_rpg:iron_knuckle'], ['forcemaster_rpg:diamond_knuckle'], ['forcemaster_rpg:netherite_knuckle']),
        weapon_words=('iron Knuckles', 'diamond Knuckles', 'netherite Knuckles'),
        sets=('forcemaster_rpg:oriene_chest', 'forcemaster_rpg:phasleb_chest', 'forcemaster_rpg:aken_chest'),
        set_names=('Oriene Suit', 'Phasleb Suit', 'Aken Suit'),
        armory=[('Billporon Suit', 'forcemaster_rpg:billporon_chest', "Ascetic's Lost Crystal")],
        armor_job='smith', weapon_job='Smith', shop=None, mats='oriene',
        legend=['forcemaster_rpg:unique_knuckle_0', 'forcemaster_rpg:unique_knuckle_1'], legend_words='knuckles'),
    'archer': dict(
        weapons=(['archers:composite_longbow', 'archers:iron_spear'],
                 ['archers:royal_longbow', 'archers:mechanic_shortbow', 'archers:diamond_spear'],
                 ['archers:netherite_longbow', 'archers:netherite_shortbow', 'archers:netherite_spear']),
        weapon_words=('a Composite Longbow or an iron Spear', 'a Royal Longbow, Mechanic Shortbow or diamond Spear',
                      'a netherite Longbow, Shortbow or Spear'),
        sets=('archers:archer_armor_chest', 'archers:ranger_armor_chest', 'archers:netherite_ranger_armor_chest'),
        set_names=('Archer Armor', 'Ranger Armor', 'Netherite Ranger Armor'),
        armory=[('Strider Armor', 'armory_rpgs:strider_armor_chest', "Vanquisher's Lost Crystal"),
                ('Riftstalker Armor', 'armory_rpgs:riftstalker_armor_chest', "Vanquisher's Forgotten Crystal")],
        armor_job='hunter', weapon_job='Hunter', shop='range', mats='archer',
        legend=[f'{ARS}:unique_{t}_{n}' for t in ('longbow', 'spear') for n in ('1', '2', 'sw')], legend_words='longbow or spear'),
    'deadeye': dict(
        weapons=bows('archers:composite_longbow'),
        weapon_words=('a Composite Longbow', 'a Royal Longbow or Mechanic Shortbow', 'a netherite Longbow or Shortbow'),
        sets=('archers:archer_armor_chest', 'archers_expansion:deadeye_chest', 'archers_expansion:netherite_deadeye_chest'),
        set_names=('Archer Armor', 'Deadeye Armor', 'Netherite Deadeye Armor'),
        armory=[('Bounty Hunter Armor', 'archers_expansion:bounty_hunter_chest', "General's Lost Crystal")],
        armor_job='hunter', weapon_job='Hunter', shop='range', mats='archer',
        legend=[f'{ARS}:unique_longbow_{n}' for n in ('1', '2', 'sw')], legend_words='longbow'),
    'tundra_hunter': dict(
        weapons=bows('archers:composite_longbow'),
        weapon_words=('a Composite Longbow', 'a Royal Longbow or Mechanic Shortbow', 'a netherite Longbow or Shortbow'),
        sets=('archers:archer_armor_chest', 'archers_expansion:tundra_hunter_chest', 'archers_expansion:netherite_tundra_hunter_chest'),
        set_names=('Archer Armor', 'Tundra Armor', 'Netherite Tundra Armor'),
        armory=[('Polar Stalker Armor', 'archers_expansion:polar_stalker_chest', "Ravager's Lost Crystal")],
        armor_job='hunter', weapon_job='Hunter', shop='range', mats='archer',
        legend=[f'{ARS}:unique_longbow_{n}' for n in ('1', '2', 'sw')], legend_words='longbow'),
    'war_archer': dict(
        weapons=(['minecraft:crossbow'], ['archers:rapid_crossbow', 'archers:heavy_crossbow'],
                 ['archers:netherite_rapid_crossbow', 'archers:netherite_heavy_crossbow']),
        weapon_words=('a Crossbow', 'a Rapid or Heavy Crossbow', 'a netherite Rapid or Heavy Crossbow'),
        sets=('archers:archer_armor_chest', 'archers_expansion:war_archer_chest', 'archers_expansion:netherite_war_archer_chest'),
        set_names=('Archer Armor', 'Bowman Armor', 'Netherite Bowman Armor'),
        armory=[('Sentinel Archer Armor', 'archers_expansion:sentinel_archer_chest', "General's Lost Crystal")],
        armor_job='hunter', weapon_job='Hunter', shop='range', mats='archer',
        legend=[f'{ARS}:unique_heavy_crossbow_{n}' for n in ('1', '2', 'sw')], legend_words='heavy crossbow'),
    'bard': dict(
        weapons=(['bards_rpg:iron_rapier', 'bards_rpg:wooden_lute', 'bards_rpg:harp_crossbow'],
                 ['bards_rpg:diamond_rapier', 'bards_rpg:diamond_lute', 'bards_rpg:diamond_lyre', 'bards_rpg:diamond_harp_crossbow'],
                 ['bards_rpg:netherite_rapier', 'bards_rpg:netherite_lute', 'bards_rpg:netherite_lyre', 'bards_rpg:netherite_harp_crossbow']),
        weapon_words=('an iron Rapier, a Lute or a Harp Crossbow', 'a diamond Rapier, Lute, Lyre or Harp Crossbow',
                      'a netherite Rapier, Lute, Lyre or Harp Crossbow'),
        sets=('bards_rpg:entertainer_garb_chest', 'bards_rpg:troubadour_garb_chest', 'bards_rpg:netherite_troubadour_garb_chest'),
        set_names=('Entertainer Garb', 'Troubadour Garb', 'Netherite Troubadour Garb'),
        armory=[('Storyteller Garb', 'bards_rpg:storyteller_garb_chest', "Virtuoso's Lost Crystal")],
        armor_job='enchanter', weapon_job='Smith (rapier), Enchanter (lute, lyre) or Hunter (harp crossbow)', shop='pub',
        mats='bard',
        legend=['bards_rpg:unique_rapier_0', 'bards_rpg:unique_rapier_1', 'bards_rpg:unique_lute_0', 'bards_rpg:unique_lute_1',
                'bards_rpg:unique_lyre_0', 'bards_rpg:unique_lyre_1', 'bards_rpg:unique_harp_crossbow_0',
                'bards_rpg:unique_harp_crossbow_1', 'bards_rpg:elder_guardian_harp_crossbow'],
        legend_words='instrument, rapier or harp crossbow'),
}

# Where each tier drops (config/rpg_series/loot_equipment_v2.json boss ladder and the zone dungeons).
LOOT_WHERE = {
    1: 'Hearthlands chests, small dungeons and the Amethyst Crab',
    2: 'Wildlands and Frontier dungeons, and the Ancient Remnant, Maledictus, the Leviathan and Scylla',
    3: 'the Harbinger and the Netherite Monstrosity',
}
LEVEL = {1: 0, 2: 10, 3: 20}  # 0: anyone can craft it
ROW_FAMILY_ORDER = ['arcane_wizard', 'fire_wizard', 'frost_wizard', 'water_mage', 'earth_mage', 'wind_mage', 'priest',
                    'paladin', 'warrior', 'berserker', 'forcemaster', 'rogue', 'archer', 'deadeye', 'tundra_hunter',
                    'war_archer', 'bard']


def calling_routes(c, tier, what, items):
    """The three ways to get a tier: craft (job and level), buy (class merchant), loot (where)."""
    job = c['weapon_job'] if what == 'weapon' else JOB_NAME[c['armor_job']]
    lines = [f'&6Craft&r: {job} level {LEVEL[tier]}' + (', or any friend who is one.' if tier == 2 else '.')]
    if not LEVEL[tier] or all(i.startswith('minecraft:') for i in items):
        lines[0] = '&6Craft&r: anyone can, at a crafting table.'
    if tier == 3:
        lines[0] = (f'&6Craft&r: at a smithing table, the diamond piece + a netherite ingot + a netherite upgrade '
                    f'template ({job} level {LEVEL[3]}).')
    if c['shop'] and tier < 3:
        lines.append(f'&6Buy&r: {SHOP[c["shop"]]} may have it in stock.')
    lines.append(f'&6Loot&r: {LOOT_WHERE[tier]}.')
    return lines


def calling_row(key, row):
    c = CALLING[key]
    title = next(k[1] for k in KITS if k[0] == key)
    y = row * 2.5
    p = f'calling/{key}'
    sub = dict(hide_until_deps_visible=True)
    weapon_mats = [r_item(item, n) for item, n in T1_MATS[c['mats']]]
    quests = [
        Q(f'cl_{key}_start', f'The {title}\'s Path', 0, y, [
            f'Every {title} walks the same road: a weapon, then a full set of armor, each tier stronger than the last.',
            'This row follows it from your first steel to the armor of legends.',
            '',
            'Each step can be &ocrafted&r, &obought&r or &olooted&r, and says how. Gear you already own counts as soon '
            'as the step opens.'],
            [t_adv(f'minerpg:{p}/start', f'Carry the {title} tome')], [r_xp(50)],
            subtitle='Your class, step by step', shape='hexagon', size=Double(1.25), invisible=True,
            invisible_until_tasks=1,
            icon={'id': 'spell_engine:spell_book', 'components': book(next(k[2] for k in KITS if k[0] == key))}),
    ]
    steps = [
        ('w1', 'First Steel', 1, 'weapon', 0, weapon_mats),
        ('s1', c['set_names'][0], 1, 'set', 0, [r_item('minecraft:diamond', 3), r_coins(1)]),
        ('w2', 'A Diamond Edge', 2, 'weapon', 1, [r_item('minecraft:diamond', 2)]),
        ('s2', c['set_names'][1], 2, 'set', 1, [r_item('minecraft:netherite_upgrade_smithing_template'), r_coins(2)]),
        ('w3', 'Forged in Netherite', 3, 'weapon', 2, [r_item('minecraft:netherite_ingot')]),
        ('s3', c['set_names'][2], 3, 'set', 2, [r_levels(5), r_coins(3), r_item('armory_rpgs:epic_armor_upgrade')]),
    ]
    prev = f'cl_{key}_start'
    for i, (step, name, tier, what, idx, rewards) in enumerate(steps):
        if what == 'weapon':
            desc = [f'Get {c["weapon_words"][idx]}.', ''] + calling_routes(c, tier, 'weapon', c['weapons'][idx])
            task = has_any(f'{p}/{step}', c['weapons'][idx], f'Have {c["weapon_words"][idx]}')
            subtitle = f'Tier {tier} weapon'
        else:
            desc = [f'Wear or carry all four pieces of the &e{name}&r: helmet, chest, legs and boots.', ''] + \
                calling_routes(c, tier, 'armor', pieces(c['sets'][idx]))
            task = has_sets(f'{p}/{step}', [pieces(c['sets'][idx])], f'All four pieces of the {name}')
            subtitle = f'Tier {tier} armor'
        quests.append(Q(f'cl_{key}_{step}', name, 1.5 * (i + 1), y, desc, [task], rewards, deps=[prev],
                        subtitle=subtitle, **sub))
        prev = f'cl_{key}_{step}'
    armory = c['armory']
    if len(armory) == 1:
        name, chest, crystal = armory[0]
        choice = [f'The endgame set of every {title}: the &d{name}&r.',
                  f'At a smithing table, upgrade each {c["set_names"][1]} piece (diamond or netherite) with a &d{crystal}&r.']
        title_text = name
    else:
        choice = [f'Two endgame sets answer a {title}. Either one completes this step:',
                  f'- &d{armory[0][0]}&r: {c["set_names"][1]} piece + &d{armory[0][2]}&r',
                  f'- &d{armory[1][0]}&r: {c["set_names"][1]} piece + &d{armory[1][2]}&r',
                  'Upgrade each piece at a smithing table (diamond or netherite pieces both work).']
        title_text = f'{armory[0][0]} or {armory[1][0]}'
    quests.append(Q(f'cl_{key}_armory', 'The Armory', 1.5 * 7, y, choice + [
        '',
        'Every upgrade also takes an &dArmory template&r, copied at a crafting table with diamonds.',
        'Crystals and templates drop from &cIgnis&r, the &5Ender Guardian&r, the &5Ender Dragon&r and the &8Wither&r.',
        f'Only {"an" if c["armor_job"] == "enchanter" else "a"} {JOB_NAME[c["armor_job"]]} of level 25 can do the '
        'upgrade; anyone can wear it.'],
        [has_sets(f'{p}/armory', [pieces(chest) for _, chest, _ in armory], f'All four pieces: {title_text}')],
        [r_levels(10), r_coins(5)], deps=[prev], subtitle='Endgame armor', shape='gear', size=Double(1.5), **sub))
    quests.append(Q(f'cl_{key}_legend', 'A Legend in Hand', 8.25, y + 1.2, [
        f'No smith makes these. The &5Ender Guardian&r, the &5Ender Dragon&r and the &8Wither&r carry one-of-a-kind '
        f'weapons; one of them may be a {c["legend_words"]} made for you.',
        'Bring friends: these are the hardest fights in the world.'],
        [has_any(f'{p}/legend', c['legend'], f'A legendary {c["legend_words"]}')], [r_levels(5)],
        deps=[f'cl_{key}_w3'], subtitle='Optional: boss-only weapon', shape='diamond', optional=True, **sub))
    return quests


# Always visible, so the tab is not empty before a class is chosen.
CALLING_INTRO = Q('cl_intro', 'Your Calling', -2.5, 0, [
    'Your class\'s road appears here once you have chosen it: a weapon, then a full set of armor, tier after tier, '
    'up to the armor of legends.',
    '',
    'No class yet? &6Choose Your Calling&r in Getting Started. Bound a second class at a Spell Binding Table? Its road '
    'appears here too, a moment after the tome is in your bag or its slot.'],
    [t_check('Understood')], [r_xp(20)], subtitle='Start here', shape='hexagon', size=Double(1.5))
CALLING_TAB = [CALLING_INTRO] + [q for row, key in enumerate(ROW_FAMILY_ORDER) for q in calling_row(key, row)]
assert set(ROW_FAMILY_ORDER) == set(CALLING) == {k[0] for k in KITS}, 'every kit needs exactly one Calling row'


# --------------------------------------------------------------------------------------
# The Forge & the Library: Apotheosis (gear, gems), Apothic Enchanting, Apothic Spawners
# --------------------------------------------------------------------------------------
APO = 'apotheosis'
ENC = 'apothic_enchanting'
FORGE_TAB = [
    Q('fl_intro', 'The Forge and the Library', 0, 2, [
        'Gear in this world is more than its name. Every magic item rolls &obonuses&r (affixes), can hold &ogems&r, '
        'and can be broken down, reforged and fine-tuned.',
        'Enchanting reaches far past level 30 once the right shelves stand around the table.',
        '',
        'This tab walks through both. Rarity and world tiers are in Getting Started.'],
        [t_check('Show me')], [r_item(f'{APO}:gem_dust', 4)], subtitle='Apotheosis, step by step', shape='hexagon',
        size=Double(1.5)),
    # Gear row
    Q('fl_salvage', 'Nothing Goes to Waste', 2, 0, [
        'A &6Salvaging Table&r breaks affixed gear into the materials of its rarity. Keep what you wear; salvage the rest.',
        'Smiths earn job experience for every piece they salvage.'],
        [has_any('guide/salvaging_table', [f'{APO}:salvaging_table'], 'Have a Salvaging Table')],
        [r_item(f'{APO}:gem_dust', 6)], deps=['fl_intro'], subtitle='Break gear down'),
    Q('fl_reforge', 'A Second Forging', 3.5, 0, [
        'A &6Reforging Table&r rerolls the bonuses of a piece of gear, and can raise its rarity. It costs rarity '
        'materials and gem dust.',
        'Reforging to &9Rare&r needs a Smith of level 10, &5Epic&r 20, &6Mythic&r 30.'],
        [has_any('guide/reforging_table', [f'{APO}:reforging_table', f'{APO}:simple_reforging_table'], 'Have a Reforging Table')],
        [r_item(f'{APO}:gem_dust', 12)], deps=['fl_salvage'], subtitle='Reroll and upgrade gear'),
    Q('fl_augment', 'The Final Polish', 5, 0, [
        'The &6Augmenting Table&r fine-tunes the bonuses of your very best gear. JEI shows what it costs.',
        'Save it for the pieces you mean to keep.'],
        [has_any('guide/augmenting_table', [f'{APO}:augmenting_table'], 'Have an Augmenting Table')],
        [r_levels(3)], deps=['fl_reforge'], subtitle='Endgame tuning'),
    # Gems row
    Q('fl_gem', 'Stones of Power', 2, 1.5, [
        '&dGems&r drop from monsters and chests. Each one gives a different bonus depending on where it sits: weapon, '
        'armor, or anything else.',
        'Hover over a gem to read all its bonuses.'],
        [has_any('guide/gem', [f'{APO}:gem'], 'Find a gem')], [r_item(f'{APO}:gem_dust', 4)], deps=['fl_intro'],
        subtitle='Find a gem'),
    Q('fl_socket', 'Set in Stone', 3.5, 1.5, [
        'Gems go into &osockets&r. Some gear rolls with sockets already; a &6Sigil of Socketing&r adds one at a '
        'smithing table.',
        'Then put the gem in at the smithing table too: gear + gem. Jewelers earn job experience for both.'],
        [has_any('guide/socketing', [f'{APO}:sigil_of_socketing'], 'Have a Sigil of Socketing')],
        [r_item(f'{APO}:gem_dust', 6)], deps=['fl_gem'], subtitle='Add sockets'),
    Q('fl_withdraw', 'Second Thoughts', 5, 1.5, [
        'Socketed a gem into the wrong sword? A &6Sigil of Withdrawal&r at the smithing table takes the gems back out, '
        'unharmed.'],
        [has_any('guide/withdrawal', [f'{APO}:sigil_of_withdrawal'], 'Have a Sigil of Withdrawal')], [r_levels(1)],
        deps=['fl_socket'], subtitle='Remove gems'),
    Q('fl_cut', 'The Gem Cutter', 3.5, 3, [
        'A &6Gem Cutting Table&r combines gems (and gem dust) into a gem of higher purity. Higher purity, bigger '
        'bonuses.',
        'Jewelers earn job experience cutting gems.'],
        [has_any('guide/gem_cutting_table', [f'{APO}:gem_cutting_table'], 'Have a Gem Cutting Table')],
        [r_item(f'{APO}:gem_dust', 8)], deps=['fl_gem'], subtitle='Raise gem purity'),
    Q('fl_charm', 'Bottled Luck', 5, 3, [
        'A &6Potion Charm&r holds a potion and gives its effect while it sits in your inventory, until it wears out.',
        'Alchemists earn job experience making them.'],
        [has_any('guide/potion_charm', [f'{APO}:potion_charm'], 'Have a Potion Charm')], [r_item('minecraft:glass_bottle', 4)],
        deps=['fl_intro'], subtitle='Effects that last'),
    # Enchanting row
    Q('fl_ench', 'Beyond Level 30', -2, 0, [
        'Enchanting here has three stats, shown on the table: &aEterna&r (how high the level goes), &cQuanta&r (how '
        'wild the result) and &dArcana&r (how many and how rare the enchantments).',
        'Every shelf around the table adds to them. Plain bookshelves reach level 30; the shelves below go further.'],
        [t_adv(f'{ENC}:30ench', 'Enchant at level 30')], [r_item('minecraft:lapis_lazuli', 16)], deps=['fl_intro'],
        subtitle='How the enchanting table works'),
    Q('fl_hell_sea', 'Hell and Sea', -3.5, 0, [
        '&cHellshelves&r (Nether bricks) and &bSeashelves&r (prismarine) are the first step past level 30.',
        'Making them needs an &dEnchanter&r of level 10; their upgrades level 20.'],
        [t_adv(f'{ENC}:hellshelf', 'Have a Hellshelf'), t_adv(f'{ENC}:seashelf', 'Have a Seashelf')],
        [r_levels(3)], deps=['fl_ench'], subtitle='Enchanter 10'),
    Q('fl_60', 'Mastering Hell and Sea', -5, 0, [
        'Infuse your shelves at the enchanting table itself, then upgrade them. Enchant at level 60.'],
        [t_adv(f'{ENC}:60ench', 'Enchant at level 60')], [r_levels(5)], deps=['fl_hell_sea'], subtitle='Enchanter 20'),
    Q('fl_deep', 'Into the Deep', -5, 1.5, [
        '&8Deepshelves&r and &8Sculkshelves&r (a Warden Tendril for the sculk ones) need an Enchanter of level 25. '
        'Enchant at level 80.'],
        [t_adv(f'{ENC}:80ench', 'Enchant at level 80')], [r_levels(7)], deps=['fl_60'], subtitle='Enchanter 25'),
    Q('fl_end', 'Dragon-Slaying Enchanter', -5, 3, [
        '&5Endshelves&r take Infused Dragon\'s Breath and an Enchanter of level 30. Enchant at level 100, the top.'],
        [t_adv(f'{ENC}:100ench', 'Enchant at level 100')], [r_levels(10)], deps=['fl_deep'], subtitle='Enchanter 30'),
    Q('fl_library', 'The Library', -3.5, 1.5, [
        'A &6Library&r stores enchanted books as points and hands out any enchantment you have stored, at any level '
        'up to the best you put in. The &6Ender Library&r holds far more.',
        'Feed it the books you will never use.'],
        [has_any('guide/library', [f'{ENC}:library', f'{ENC}:ender_library'], 'Have a Library')], [r_item('minecraft:book', 8)],
        deps=['fl_ench'], subtitle='Store enchantments'),
    # Spawners
    Q('fl_spawner', 'Caged Monsters', -2, 3, [
        'Spawners can be picked up with a &6Silk Touch&r pickaxe (not inside the great dungeons, where the stone '
        'will not break), carried home and modified.',
        'Right-click a spawner with the right item to change it; JEI lists every modifier.'],
        [t_adv('apothic_spawners:modifier', 'Modify a spawner')], [r_levels(5)], deps=['fl_intro'],
        subtitle='Collect and modify spawners', optional=True),
]


# --------------------------------------------------------------------------------------
# The Adventurer's Kit: the other mods worth knowing
# --------------------------------------------------------------------------------------
TBP = 'travelersbackpack'
KIT_TAB = [
    Q('ak_intro', 'The Adventurer\'s Kit', 0, 0, [
        'Small things that make a long road easier: jewelry, a backpack, a storage room, a kitchen, and what to do '
        'when things go wrong.',
        '',
        'Already in Getting Started: rolling (R), reviving friends, parties (H), waystones, the cooking pot, '
        'salvaging and your own chest loot.'],
        [t_check('Show me')], [r_item('minecraft:emerald', 2)], subtitle='Everything else, step by step', shape='hexagon',
        size=Double(1.5)),
    # Jewelry and relics
    Q('ak_jeweler', 'The Jeweler', 2, -1.5, [
        'Villages with a &6Jeweler&r trade gems, rings and necklaces. Gem veins hide underground too.',
        'Or take up the &3Jeweler&r job (J) and make them yourself.'],
        [t_adv('trade_jeweler', 'Trade with a Jeweler')], [r_item('minecraft:gold_ingot', 4)], deps=['ak_intro'],
        subtitle='Rings and necklaces'),
    Q('ak_ring', 'A Ring for Each Hand', 3.5, -2, [
        'Rings and necklaces go in their own slots (G opens them) and add spell power, health or speed.',
        'Copper and iron rings anyone can craft. Gem and gold jewelry takes a Jeweler of level 10; or buy one, or find one in a dungeon.'],
        [has_any('guide/ring', '#curios:ring', 'Have a ring')], [r_item('minecraft:gold_ingot', 3)], deps=['ak_jeweler'],
        subtitle='Ring slot'),
    Q('ak_necklace', 'Close to the Heart', 3.5, -1, [
        'One necklace at a time. Pick the one that matches your class\'s power.'],
        [has_any('guide/necklace', '#curios:necklace', 'Have a necklace')], [r_item('minecraft:string', 4)],
        deps=['ak_jeweler'], subtitle='Necklace slot'),
    Q('ak_gem_cut', 'Cut to Fit', 3.5, -3.5, [
        'The &6Jeweler\'s Kit&r cuts the jeweler\'s gems (ruby, sapphire, jade, topaz, citrine, tanzanite) to fit into '
        'armor. Put a gem in and pick one of its four cuts: the cut decides the bonus.',
        'Shadowy Tanzanite adds soul spell power, Fierce Ruby critical damage, the sapphires health and armor. Hover '
        'over each cut to compare.',
        'Jewelers earn job experience for every gem they cut.'],
        [has_any('guide/jewelers_kit', ['jewelry:jewelers_kit'], 'Have a Jeweler\'s Kit')], [r_item('jewelry:ruby', 2)],
        deps=['ak_jeweler'], subtitle='Gem cutting'),
    Q('ak_socket_mount', 'Set in Gold', 5, -3.5, [
        'Armor has no sockets of its own. A &6Socket Mount&r adds one: put the armor and the mount in an &6anvil&r. '
        'Each piece takes one.',
        'Then put the armor and a cut gem in the anvil to set the gem. A full set holds four. The Jeweler\'s Kit can '
        'take a gem back out.',
        'Socket Mounts are crafted by a Jeweler of level 15.'],
        [has_any('guide/socket_mount', ['jewelry:socket_mount'], 'Have a Socket Mount')], [r_item('minecraft:diamond', 1)],
        deps=['ak_gem_cut'], subtitle='Sockets for armor'),
    Q('ak_relic', 'Relics', 5, -1.5, [
        '&dRelics&r are trinkets with a single strong effect: heal on a kill, a burst of speed, a ward against death.',
        'Most drop from bosses and deep dungeons.'],
        [has_any('guide/relic', '#relics_rpgs:all', 'Find a relic')], [r_levels(3)], deps=['ak_ring', 'ak_necklace'],
        subtitle='Trinket slot'),
    # Backpack
    Q('ak_backpack', 'Everything You Own, On Your Back', 2, 1, [
        'A &6Traveler\'s Backpack&r carries a chest\'s worth of items, two fluid tanks and a sleeping bag. Wear it; '
        'B opens it.',
        'JEI shows the recipe, and the dozens of other looks a backpack can be crafted in.'],
        [t_adv(f'{TBP}:standard', 'Craft a backpack')], [r_item('minecraft:leather', 6)], deps=['ak_intro'],
        subtitle='Traveler\'s Backpack'),
    Q('ak_backpack_upgrade', 'Room to Grow', 3.5, 1, [
        'Tier upgrades (iron, gold, diamond, netherite) add rows of slots. Other upgrades add a crafting grid, a '
        'furnace, a magnet or auto-feeding.'],
        [t_adv(f'{TBP}:iron_upgrade', 'Upgrade a backpack to iron')], [r_item('minecraft:iron_ingot', 6)],
        deps=['ak_backpack'], subtitle='Backpack upgrades'),
    Q('ak_sleeping_bag', 'Camp Anywhere', 5, 1, [
        'Unroll the backpack\'s sleeping bag to sleep out in the wild, far from any bed.'],
        [t_adv(f'{TBP}:use_sleeping_bag', 'Sleep in a sleeping bag')], [r_item('minecraft:torch', 16)],
        deps=['ak_backpack'], subtitle='Sleeping bag', optional=True),
    # Storage
    Q('ak_terminal', 'One Window for Every Chest', 2, 2.5, [
        'Tom\'s Storage turns a room of chests into one searchable window. Put an &6Inventory Connector&r touching your '
        'chests (or linked to them by cables) and a &6Storage Terminal&r next to it.',
        'With a Wireless Terminal in your pocket, M opens it from nearby.'],
        [has_any('guide/storage_terminal', ['toms_storage:storage_terminal', 'toms_storage:crafting_terminal'],
                 'Have a Storage Terminal')],
        [r_item('minecraft:chest', 4)], deps=['ak_intro'], subtitle='Tom\'s Simple Storage'),
    # Kitchen
    Q('ak_kitchen', 'A Proper Kitchen', -2, -1.5, [
        'A &6Cutting Board&r slices with a knife; a &6Skillet&r cooks over heat. Together with the cooking pot they '
        'make every Farmer\'s Delight meal.',
        'Cooks earn job experience for every meal. Plated meals need a Cook of level 10, feasts a Cook of level 20.'],
        [has_any('guide/cutting_board', ['farmersdelight:cutting_board'], 'Have a Cutting Board'),
         has_any('guide/skillet', ['farmersdelight:skillet'], 'Have a Skillet')],
        [r_item('farmersdelight:rice', 8), r_item('farmersdelight:onion', 4)], deps=['ak_intro'], subtitle='Farmer\'s Delight'),
    # When things go wrong
    Q('ak_survey', 'Charting the Unknown', -3.5, -1.5, [
        'An &9Explorer&r (J) draws &6Survey Maps&r: use one and it becomes a map to the nearest place of its kind.',
        '- Settlement (map + emerald): anyone can draw it. Villages and taverns.',
        '- Crypt (Explorer 10), Great Dungeon (Explorer 20), Boss Lair (Explorer 30).',
        'Copy the finished map at a &6cartography table&r so everyone in the party has one.',
        'Explorers also craft the travel network: scrolls, Sharestones (every stone of one color links to the others), Waystones and Warp Plates.'],
        [has_any('guide/survey_map', ['minerpg:survey_map_settlement', 'minerpg:survey_map_crypt',
                                      'minerpg:survey_map_dungeon', 'minerpg:survey_map_lair'], 'Have a Survey Map')],
        [r_item('minecraft:map', 2)], deps=['ak_intro'], subtitle='Explorer'),
    Q('ak_grave', 'If You Fall', -2, 1, [
        'If you are downed, a friend can pick you up. If you truly die, nothing is lost: your items, armor, trinkets, '
        'backpack and experience wait in a &6grave&r. The chat says where, and you respawn with a compass to it.',
        'Only you can open it for 15 minutes; after that a friend may collect it for you.'],
        [t_check('Understood')], [r_item('minecraft:compass')], deps=['ak_intro'], subtitle='Graves'),
    Q('ak_claim', 'This Land Is Mine', -2, 2.5, [
        'Claim the chunks of your home so nobody else can break or open anything there.',
        'Press F3+G to see chunk borders. Stand inside one and type &e/oclaims claim&r; &e/oclaims unclaim&r gives it '
        'back. &e/oclaims anchor&r places a claiming anchor that claims the area around it.',
        'Party members share claims; the \' key opens the menu with more options.',
        'Each player can claim up to 500 chunks.'],
        [t_check('I have claimed my home')], [r_item('minecraft:oak_sign', 4)], deps=['ak_intro'], subtitle='Land claims'),
    Q('ak_elites', 'Not Just Another Zombie', -3.5, 1, [
        'Some monsters are &celites&r: a title over their heads and special powers, from shields to reflecting '
        'damage. They hit harder and drop better loot.',
        'Fight them with your party, or not at all.'],
        [t_check('Understood')], [r_xp(30)], deps=['ak_intro'], subtitle='Champions'),
]


CHAPTERS = [
    ('getting_started', 'Getting Started', ['How everything works, one quest at a time.'], 'minecraft:writable_book', GETTING_STARTED),
    ('your_calling', 'Your Calling', ['Your class, from the tome to the armor of legends.'], 'spell_engine:spell_book', CALLING_TAB),
    ('chapter_1_overworld', 'Chapter 1: The Overworld', ['Hearthlands, Wildlands and the Frontier. Ends with The Harbinger.'], 'minecraft:grass_block', CHAPTER_1),
    ('chapter_2_nether', 'Chapter 2: The Nether', ['Fortresses, bastions and fire. Ends with Ignis.'], 'minecraft:netherrack', CHAPTER_2),
    ('chapter_3_end', 'Chapter 3: The End', ['The dragon, the cities and the citadel.'], 'minecraft:end_stone', CHAPTER_3),
    ('forge_and_library', 'The Forge & the Library', ['Affixes, gems, reforging, enchanting and spawners.'], 'apotheosis:reforging_table', FORGE_TAB),
    ('adventurers_kit', 'The Adventurer\'s Kit', ['Jewelry, backpacks, storage, cooking, graves and claims.'], 'travelersbackpack:standard', KIT_TAB),
]


# --------------------------------------------------------------------------------------
# Your Calling: the tome scan (kubejs/server_scripts/minerpg_calling.js)
# --------------------------------------------------------------------------------------
CALLING_SCRIPT = os.path.join(ROOT, 'kubejs', 'server_scripts', 'minerpg_calling.js')


def write_calling_script():
    pools = {pool: key for key, _, pool, _, _, _ in KITS}
    write(CALLING_SCRIPT, """// minerpg: open a class's row in the "Your Calling" quest tab when the player has that class's tome.
// GENERATED by pack/tools/gen_quests.py (edit the generator, not this file).
//
// The kit function grants minerpg:calling/<kit>/start when a kit is chosen. A second class bound later at a Spell
// Binding Table never runs a kit, so every 2 s this checks each player's inventory and spell book slot for a tome
// and grants the row of its class. A tome's class is the pool in its spell_engine:spell_container component.

const $CallingCurios = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')

const CALLING_POOLS = %s

// player name -> {kit: true} already granted this session (the grant command is a no-op after the first time)
const callingSeen = {}

function callingCheckStack(player, stack, seen) {
  if (stack.isEmpty() || stack.id != 'spell_engine:spell_book') return
  const text = String(stack.getComponentString())
  for (const pool in CALLING_POOLS) {
    const kit = CALLING_POOLS[pool]
    if (!seen[kit] && text.indexOf('"' + pool + '"') >= 0) {
      seen[kit] = true
      player.server.runCommandSilent('advancement grant ' + player.username + ' only minerpg:calling/' + kit + '/start')
    }
  }
}

function callingScan(player) {
  const seen = callingSeen[player.username] || (callingSeen[player.username] = {})
  const inv = player.inventory
  for (let i = 0; i < inv.getContainerSize(); i++) callingCheckStack(player, inv.getItem(i), seen)
  const curios = $CallingCurios.getCuriosInventory(player).orElse(null)
  if (curios == null) return
  const equipped = curios.getEquippedCurios()
  for (let i = 0; i < equipped.getSlots(); i++) callingCheckStack(player, equipped.getStackInSlot(i), seen)
}

PlayerEvents.loggedOut(event => {
  delete callingSeen[event.player.username]
})

let callingTicks = 0
ServerEvents.tick(event => {
  callingTicks++
  if (callingTicks %% 40 != 0) return
  event.server.players.forEach(player => {
    try {
      callingScan(player)
    } catch (err) {
      console.error('minerpg calling: scan failed for ' + player.username + ': ' + err)
    }
  })
})
""" % json.dumps(pools, indent=2))


# --------------------------------------------------------------------------------------
# Item id check (optional): every modded id the quests use must exist in the installed jars
# --------------------------------------------------------------------------------------
def check_item_ids(mods_dir):
    """Fail the build on an item id no jar defines (a typo makes a task silently impossible).
    Vanilla ids and tags are not checked."""
    known = set()
    for jar in glob.glob(os.path.join(mods_dir, '*.jar')):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                m = re.match(r'assets/([^/]+)/models/item/([^/]+)\.json$', name)
                if m:
                    known.add(f'{m.group(1)}:{m.group(2)}')
    used = set()

    def walk(v):
        if isinstance(v, str):
            if re.fullmatch(r'[a-z0-9_]+:[a-z0-9_/]+', v) and not v.startswith(('minecraft:', 'minerpg:')):
                used.add(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
    # Ids in "has an item" tasks (trigger names are minecraft: ids and skipped) and in item rewards.
    for criteria, _ in HAS_ADV.values():
        walk(criteria)
    walk(QUEST_ICONS)
    for _, _, _, _, quests in CHAPTERS:
        for qd in quests:
            for r in qd['rewards']:
                if r.get('type') == 'item':
                    walk(r['item']['id'])
    missing = sorted(i for i in used if i not in known)
    if missing:
        raise SystemExit('unknown item ids: ' + ', '.join(missing))
    print(f'item ids checked: {len(used)} modded ids, all present')


# --------------------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# Quest icons. FTB shows a quest with the icon of its first task; our helper advancements have no
# display, so without an explicit icon those quests fell back to a placeholder (wheat). Order:
# an icon passed to Q(), then QUEST_ICONS, then the first item a "has an item" task looks for,
# then ADV_ICONS for the named helper advancements.
# --------------------------------------------------------------------------------------
QUEST_ICONS = {
    # Getting Started
    'gs_welcome': 'minecraft:map', 'gs_race': 'minecraft:armor_stand', 'gs_calling': 'spell_engine:spell_book',
    'gs_cast': 'minecraft:fire_charge', 'gs_runes': 'runes:arcane_stone', 'gs_binding': 'spell_engine:spell_binding',
    'gs_talent': 'minecraft:experience_bottle', 'gs_roll': 'minecraft:feather', 'gs_stats': 'minecraft:iron_chestplate',
    'gs_waystone': 'waystones:waystone', 'gs_lootr': 'lootr:lootr_chest', 'gs_locks': 'minecraft:trial_key',
    'gs_party': 'minecraft:cake', 'gs_jobs': 'minecraft:iron_pickaxe', 'gs_job_gates': 'minecraft:crafting_table',
    'gs_revive': 'minecraft:golden_apple', 'gs_tour': 'minecraft:emerald',
    'gs_job_alchemist': 'minecraft:brewing_stand', 'gs_job_enchanter': 'minecraft:enchanting_table',
    'gs_job_smith': 'minecraft:smithing_table',
    'cl_intro': 'spell_engine:spell_book',
    # Chapter 1: the Overworld (Cataclysm lairs show the eye that finds them)
    'c1_village': 'minecraft:bell', 'c1_tavern': 'minecraft:barrel', 'c1_cellar': 'minecraft:mossy_cobblestone',
    'c1_nest': 'cataclysm:altar_of_amethyst', 'c1_wild': 'minecraft:compass',
    'c1_rumor_pyramid': 'minecraft:map', 'c1_rumor_prison': 'minecraft:map', 'c1_rumor_sunken': 'minecraft:map',
    'c1_pyramid': 'cataclysm:desert_eye', 'c1_prison': 'cataclysm:cursed_eye', 'c1_sunken': 'cataclysm:abyss_eye',
    'c1_frontier': 'minecraft:sculk_shrieker', 'c1_factory': 'cataclysm:mech_eye',
    'c1_job_10': 'minecraft:iron_ingot', 'c1_job_craft': 'minecraft:crafting_table',
    # Chapter 2: the Nether
    'c2_arrive': 'minecraft:obsidian', 'c2_fortress': 'minecraft:nether_bricks', 'c2_blaze': 'minecraft:blaze_rod',
    'c2_bastion': 'minecraft:gilded_blackstone', 'c2_brutes': 'minecraft:golden_axe', 'c2_keep': 'minecraft:soul_lantern',
    'c2_smith': 'cataclysm:monstrous_eye', 'c2_arena': 'cataclysm:flame_eye', 'c2_job_20': 'minecraft:gold_ingot',
    # Chapter 3: the End
    'c3_stronghold': 'minecraft:ender_eye', 'c3_end': 'minecraft:end_portal_frame', 'c3_city': 'minecraft:shulker_shell',
    'c3_castle': 'minecraft:purpur_block', 'c3_citadel': 'cataclysm:void_eye', 'c3_job_30': 'minecraft:diamond',
    # The Forge & the Library
    'fl_intro': 'minecraft:enchanting_table', 'fl_ench': 'minecraft:enchanted_book', 'fl_hell_sea': 'minecraft:nether_bricks',
    'fl_60': 'minecraft:prismarine', 'fl_deep': 'minecraft:sculk', 'fl_end': 'minecraft:end_stone_bricks',
    'fl_spawner': 'minecraft:spawner',
    # The Adventurer's Kit
    'ak_intro': 'travelersbackpack:standard', 'ak_jeweler': 'jewelry:jewelers_kit', 'ak_ring': 'jewelry:gold_ring',
    'ak_necklace': 'jewelry:emerald_necklace', 'ak_relic': 'minecraft:heart_of_the_sea',
    'ak_backpack': 'travelersbackpack:standard', 'ak_backpack_upgrade': 'travelersbackpack:gold_tier_upgrade',
    'ak_sleeping_bag': 'travelersbackpack:red_sleeping_bag', 'ak_grave': 'minecraft:skeleton_skull',
    'ak_claim': 'minecraft:white_banner', 'ak_elites': 'minecraft:zombie_head',
}
ADV_ICONS = {}


def quest_icon(qd):
    if qd['key'] in QUEST_ICONS:
        return {'id': QUEST_ICONS[qd['key']]}
    if not qd['tasks']:
        return None
    task = qd['tasks'][0]
    if task['type'] != 'advancement':
        return None
    name = task['advancement']
    if name in ADV_ICONS:
        return {'id': ADV_ICONS[name]}
    path = name[len('minerpg:'):] if name.startswith('minerpg:') else None
    if path in HAS_ADV:
        criteria = HAS_ADV[path][0]
        if 'has' in criteria:
            first = criteria['has']['conditions']['items'][0]['items'][0]
        else:
            # A set: show the chest piece (second of head/chest/legs/feet).
            pieces = criteria['set_0']['conditions']['items']
            first = pieces[1 if len(pieces) > 1 else 0]['items'][0]
        if not first.startswith('#'):
            return {'id': first}
    return None


def resolve_adv(task):
    if task['type'] == 'advancement' and task['advancement'] in ADV:
        task['advancement'] = ADV[task['advancement']]
    return task


def build(mods_dir=None):
    write_kit_functions()
    write_advancements()
    write_structure_tags()
    write_maps()

    if os.path.isdir(QUESTS):
        shutil.rmtree(QUESTS)

    lang('file', '0000000000000001', 'title', 'minerpg')

    # Reward table for the class kits.
    table_id = oid('table:' + KIT_TABLE)
    lang('reward_table', table_id, 'title', 'Class starter kits')
    table_rewards = []
    for key, title, pool, weapon, armor, extras in KITS:
        rid = oid(f'table:{KIT_TABLE}:{key}')
        lang('reward', rid, 'title', title)
        table_rewards.append({
            'id': rid,
            'type': 'command',
            'command': f'/function minerpg:kit/{key}',
            'permission_level': 2,
            'silent': True,
            'icon': {'id': 'spell_engine:spell_book', 'components': book(pool)},
        })
    write(os.path.join(QUESTS, 'reward_tables', f'{KIT_TABLE}.snbt'), snbt({
        'id': table_id,
        'order_index': 0,
        'loot_size': 1,
        'use_title': True,
        'rewards': table_rewards,
    }))

    # Quest keys are global, so a quest can depend on one in another tab.
    keys = {}
    for _, _, _, _, quests in CHAPTERS:
        for qd in quests:
            if qd['key'] in keys:
                raise SystemExit(f'duplicate quest key {qd["key"]}')
            keys[qd['key']] = oid('quest:' + qd['key'])

    counts = {}
    no_icon = []
    for order, (filename, title, subtitle, icon, quests) in enumerate(CHAPTERS):
        cid = oid('chapter:' + filename)
        lang('chapter', cid, 'title', title)
        lang('chapter', cid, 'chapter_subtitle', subtitle)
        out = []
        for qd in quests:
            qid = keys[qd['key']]
            lang('quest', qid, 'title', qd['title'])
            if qd['subtitle']:
                lang('quest', qid, 'quest_subtitle', qd['subtitle'])
            lang('quest', qid, 'quest_desc', qd['desc'])
            tasks = []
            for i, task in enumerate(qd['tasks']):
                task = resolve_adv(dict(task))
                tid = oid(f'task:{qd["key"]}:{i}')
                title_text = task.pop('_title', None)
                if title_text:
                    lang('task', tid, 'title', title_text)
                task['id'] = tid
                tasks.append(task)
            rewards = []
            for i, reward in enumerate(qd['rewards']):
                reward = dict(reward)
                reward['id'] = oid(f'reward:{qd["key"]}:{i}')
                reward_title = reward.pop('_title', None)
                if reward_title:
                    lang('reward', reward['id'], 'title', reward_title)
                if reward.get('_table'):
                    reward['table_id'] = Long(int(oid('table:' + reward.pop('_table')), 16))
                rewards.append(reward)
            quest = {
                'id': qid,
                'x': Double(qd['x']),
                'y': Double(qd['y']),
                'tasks': tasks,
            }
            if rewards:
                quest['rewards'] = rewards
            if qd['deps']:
                for d in qd['deps']:
                    if d not in keys:
                        raise SystemExit(f'unknown dependency {d} in {qd["key"]}')
                quest['dependencies'] = [keys[d] for d in qd['deps']]
            for k, v in qd['extra'].items():
                quest[k] = v
            if 'icon' not in quest:
                derived = quest_icon(qd)
                if derived:
                    quest['icon'] = derived
                elif tasks[0]['type'] not in ('item',):
                    no_icon.append(f'{qd["key"]} ({tasks[0]["type"]})')
            out.append(quest)
        counts[title] = len(out)
        write(os.path.join(QUESTS, 'chapters', f'{filename}.snbt'), snbt({
            'id': cid,
            'group': '',
            'order_index': order,
            'filename': filename,
            'icon': {'id': icon},
            'default_quest_shape': '',
            'default_hide_dependency_lines': False,
            'quest_links': [],
            'quests': out,
        }))

    write(os.path.join(QUESTS, 'chapter_groups.snbt'), snbt({'chapter_groups': []}))
    write(os.path.join(QUESTS, 'data.snbt'), snbt({
        'version': 13,
        'default_reward_team': False,
        'default_consume_items': False,
        'default_autoclaim_rewards': 'disabled',
        'default_quest_shape': 'circle',
        'default_quest_disable_jei': False,
        'emergency_items_cooldown': 300,
        'drop_loot_crates': False,
        'disable_gui': False,
        'grid_scale': Double(0.5),
        'pause_game': False,
        'lock_message': '',
        # Flexible: tasks count even before a quest unlocks (you can go anywhere; the book
        # catches up when you get there).
        'progression_mode': 'flexible',
        'detection_delay': 20,
        'show_lock_icons': True,
        'drop_book_on_death': False,
        'hide_excluded_quests': False,
        'fallback_locale': 'en_us',
        'verify_on_load': False,
    }))
    write(os.path.join(QUESTS, 'lang', 'en_us.snbt'), snbt(LANG))
    write_calling_script()
    if mods_dir:
        check_item_ids(mods_dir)
    for k, v in counts.items():
        print(f'{k}: {v} quests')
    if no_icon:
        print(f'{len(no_icon)} quests show their first task\'s icon: ' + ', '.join(no_icon))
    print(f'{len(KITS)} class kits')


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else None)
