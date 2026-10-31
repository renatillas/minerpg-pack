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
import hashlib
import json
import os
import shutil

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


# Jobs+ coins (spent on new jobs and power-ups in the Jobs menu). Jobs+'s own /job command can
# only set coins, so this uses the pack's /minerpg_jobs command (kubejs/server_scripts/minerpg_jobs.js).
def r_coins(amount):
    return r_cmd(f'/minerpg_jobs coins @s {amount}', f'+{amount} job coins')


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
    for sub in ('tutorial', 'jobs', 'tour'):
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
    ADV['digger'] = adv('jobs/digger', {'dig': {'trigger': 'minecraft:inventory_changed', 'conditions': {'items': [{
        'items': ['minecraft:dirt', 'minecraft:gravel', 'minecraft:sand', 'minecraft:red_sand', 'minecraft:clay_ball'],
        'count': {'min': 32}}]}}})
    ADV['lumberjack'] = adv('jobs/lumberjack', {'logs': {'trigger': 'minecraft:inventory_changed', 'conditions': {'items': [{
        'items': '#minecraft:logs', 'count': {'min': 16}}]}}})
    ADV['builder'] = adv('jobs/builder', {'place': {'trigger': 'minecraft:placed_block', 'conditions': {}}})
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
        'Nothing is final: a second class waits at any Spell Binding Table.'],
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
        'Press J and join two jobs. Each grows from its own work and pays in coins and perks.',
        'Spend &6job coins&r in the same menu on power-ups or a third job. Every level pays a coin; many quests pay more.',
        'The quests below show one way into each job.'],
        [t_check('Join two jobs')], [r_xp(30), r_coins(3)], deps=['gs_welcome'], subtitle='Jobs menu (J)'),
    Q('gs_job_gates', 'Masters of a Trade', -13.5, 0, [
        'Some things only a trained hand can &omake&r:',
        'Class gear is made by three trades, by tier: tier 1 at level 10, diamond tier 2 at 20, netherite tier 3 at 25, Armory sets at 30.',
        '- &cSmith&r: plate armor and melee weapons (Warrior, Paladin, Berserker, Forcemaster). Reforging to Rare needs Smith 10, Epic 20, Mythic 30.',
        '- &2Hunter&r: leather armor, bows, crossbows, spears and quivers (Archer, Rogue).',
        '- &dEnchanter&r: robes, staves, wands and instruments (Wizard, mages, Priest, Bard), and the stronger enchanting shelves: Hellshelf and Seashelf at 10, their upgrades at 20, deep and sculk shelves at 25, endshelves at 30.',
        '- &5Alchemist&r: Strong and Long potions at 10, Splash at 15, Lingering at 20.',
        '',
        'Anyone can &ouse&r these things. Class gear still drops from dungeons and bosses, class merchants sell it, plain bookshelves work for everyone, and a friend with the job can make it for you.',
        'Hover over an item to see the job and level that make it.',
        'Job experience also comes from the adventure: Smiths from reforging, salvaging and socketing, Enchanters from binding spells and cutting gems, Alchemists from runes and potion charms, Hunters from skinning their kills and working leather, Farmers from the cooking pot.',
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
        'Wild cabbages, tomatoes, onions and rice grow out in the world: break them for seeds. Hover over any food to see how much it restores.'],
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

JOB_STARTERS = [
    ('alchemist', 'Alchemist', 'Alchemists earn experience brewing, crafting runes and potion charms. Brew any potion.', t_adv('alchemist', 'Brew a potion'), r_item('minecraft:glass_bottle', 6)),
    ('builder', 'Builder', 'Builders earn experience for every block they place. Place one to start.', t_adv('builder', 'Place a block'), r_item('minecraft:stone_bricks', 32)),
    ('digger', 'Digger', 'Diggers earn experience digging dirt, sand, gravel and clay. Carry 32 of one.', t_adv('digger', 'Gather 32 dirt, sand, gravel or clay'), r_item('minecraft:iron_shovel')),
    ('enchanter', 'Enchanter', 'Enchanters earn experience at the enchanting table, the Spell Binding Table and the gem cutting table. Enchant any item.', t_adv('minecraft:story/enchant_item', 'Enchant an item'), r_item('minecraft:lapis_lazuli', 12)),
    ('farmer', 'Farmer', 'Farmers earn experience harvesting grown crops and cooking pot meals. Bring in 16 wheat.', t_item('minecraft:wheat', 16), r_item('minecraft:bone_meal', 16)),
    ('fisherman', 'Fisherman', 'Fishermen earn experience for every catch. Catch a fish.', t_adv('minecraft:husbandry/fishy_business', 'Catch a fish'), r_item('minecraft:cooked_cod', 8)),
    ('hunter', 'Hunter', 'Hunters are skinners and leatherworkers. They earn experience for every hide, bone and monster part their kills drop (and find more of them as they level), for hunting animals and for crafting leather goods. Bring in 8 leather.', t_item('minecraft:leather', 8), r_item('minecraft:arrow', 32)),
    ('lumberjack', 'Lumberjack', 'Lumberjacks earn experience chopping logs. Carry 16 logs.', t_adv('lumberjack', 'Gather 16 logs'), r_item('minecraft:iron_axe')),
    ('miner', 'Miner', 'Miners earn experience breaking stone and ores. Mine 16 coal.', t_item('minecraft:coal', 16), r_item('minecraft:torch', 32)),
    ('smith', 'Smith', 'Smiths earn experience smelting ingots, crafting tools, weapons and armor, and reforging, salvaging and socketing gear. Craft an iron pickaxe.', t_adv('minecraft:story/iron_tools', 'Craft an iron pickaxe'), r_item('minecraft:iron_ingot', 6)),
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
        'At level 10, Smiths, Hunters and Enchanters make tier 1 class gear of their kind, Enchanters also the Hellshelf and Seashelf, and Alchemists brew Strong and Long potions.',
        '&7Checked when the job levels up.&r'],
        [t_adv('job_level_10', 'Reach level 10 in a job')], [r_coins(5), r_item('minecraft:emerald', 4)],
        deps=['c1_village'], subtitle='Job milestone', shape='circle', optional=True),
    Q('c1_job_craft', 'Made for a Friend', 1.5, 4.5, [
        'Make something only a trained hand can make: class gear as a Smith, Hunter or Enchanter, an enchanting shelf as an Enchanter, or a Strong, Long, Splash or Lingering potion as an Alchemist.',
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
        'At level 20, Smiths, Hunters and Enchanters make diamond class gear; Smiths reforge to Epic, Enchanters make the upgraded hell and sea shelves, and Alchemists brew Lingering potions.',
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
        'At level 30, Smiths, Hunters and Enchanters make the Armory sets from Ignis\'s upgrade crystals; Smiths reforge to Mythic and Enchanters make endshelves.',
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

CHAPTERS = [
    ('getting_started', 'Getting Started', ['How everything works, one quest at a time.'], 'minecraft:writable_book', GETTING_STARTED),
    ('chapter_1_overworld', 'Chapter 1: The Overworld', ['Hearthlands, Wildlands and the Frontier. Ends with The Harbinger.'], 'minecraft:grass_block', CHAPTER_1),
    ('chapter_2_nether', 'Chapter 2: The Nether', ['Fortresses, bastions and fire. Ends with Ignis.'], 'minecraft:netherrack', CHAPTER_2),
    ('chapter_3_end', 'Chapter 3: The End', ['The dragon, the cities and the citadel.'], 'minecraft:end_stone', CHAPTER_3),
]


# --------------------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------------------
def resolve_adv(task):
    if task['type'] == 'advancement' and task['advancement'] in ADV:
        task['advancement'] = ADV[task['advancement']]
    return task


def build():
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

    counts = {}
    for order, (filename, title, subtitle, icon, quests) in enumerate(CHAPTERS):
        cid = oid('chapter:' + filename)
        lang('chapter', cid, 'title', title)
        lang('chapter', cid, 'chapter_subtitle', subtitle)
        keys = {qd['key']: oid('quest:' + qd['key']) for qd in quests}
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
    for k, v in counts.items():
        print(f'{k}: {v} quests')
    print(f'{len(KITS)} class kits')


if __name__ == '__main__':
    build()
