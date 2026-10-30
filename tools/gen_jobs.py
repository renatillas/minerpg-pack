#!/usr/bin/env python3
"""Generate the Jobs+ integration data: crafting gates, extra job XP actions, level milestones.

Design: docs/superpowers/specs/2026-10-30-minerpg-jobs-integration-design.md ("Implementation
notes" has the gate table, XP numbers and pacing). Everything lands in the minerpg_jobs datapack
(config/originpacks/minerpg_jobs/, loaded globally by NeoOrigins):

  data/minerpg/itemrestrictions/restrictions/   Item Restrictions gates (crafting / brewing only)
  data/minerpg/tags/item/job_gate/               item tags the gates and XP bonuses share
  data/minerpg/arc/gen/                          Arc actions (job XP bonuses, milestone grants)
  data/minerpg/advancement/jobs_xp/              repeatable hidden advancements that
                                                 kubejs/server_scripts/minerpg_jobs.js turns into job XP

Run:  python3 pack/tools/gen_jobs.py <path to a server folder with the pack installed>
The server folder is read for item lists only: mods/*.jar (RPG Series armor/weapon type tags,
Armory set recipes) and config/rpg_series/tag_cache.json (RPG Series tiers, written at runtime).
Generated folders are wiped and rewritten; the hand-written Arc actions in data/minerpg/arc/<job>/
are not touched. This tools folder is excluded from the pack by pack/.packwizignore.
"""
import glob
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
PACK = os.path.join(ROOT, 'config', 'originpacks', 'minerpg_jobs', 'data', 'minerpg')

# --------------------------------------------------------------------------------------
# Gate table (single source of truth). Levels are tuned in the design doc's pacing table.
# --------------------------------------------------------------------------------------
# Class gear: RPG Series weapons and armor, split into gear groups x tiers. Tier 0 (wood, flint,
# novice wands) is free. RPG Series tags its gear by tier: tier 1 = iron-era, tier 2 = diamond,
# tier 3 = netherite (smithing upgrade); tier 4 is empty in this pack. "set" = the Armory / More
# RPG Classes set pieces made at the smithing table with an Ignis upgrade crystal.
#
# Designer revision (2026-10-30): class-gear crafting is split three ways.
#   plate   -> Smith:     plate/melee armor and melee weapons (Warrior, Paladin, Berserker,
#                         Forcemaster, Bard rapiers)
#   leather -> Hunter:    light/leather armor, bows, crossbows, spears, quivers (Archer, Archers
#                         Expansion, Rogue armor/daggers/sickles, Bard harp crossbows)
#   caster  -> Enchanter: robes, staves, wands, holy weapons, Bard instruments and garb (Wizard
#                         schools, elemental mages, Priest, Bard)
# Items are grouped from RPG Series' own type tags ("magic" armor and magic/healing weapons =
# caster, "archery" armor and ranged weapons = leather, the rest = plate), then GEAR_GROUP_OVERRIDES.
# To move a group to another job, change GEAR_GROUP_JOB and re-run (the crafting XP bonus follows).
GEAR_GROUP_JOB = {'plate': 'smith', 'leather': 'hunter', 'caster': 'enchanter'}
GEAR_GROUP_TITLE = {'plate': 'plate armor and melee weapons', 'leather': 'leather armor, bows and quivers',
                    'caster': 'caster robes, staves and wands'}
# (substring of the item id, group): first match wins, checked before the type tags.
GEAR_GROUP_OVERRIDES = [
    ('forcemaster_rpg:', 'plate'),      # Forcemaster knuckles and armor: melee class
    ('_lute', 'caster'), ('_lyre', 'caster'), ('bards_rpg:wooden_lute', 'caster'),  # Bard instruments
    ('_harp_crossbow', 'leather'),
    # Mercenaries and Artificers: ranged weapons follow their archetype (Hunter); pikes are spears
    # (Hunter, like the Archers spears); the Frontier set is chain + leather (Hunter); the
    # Commissioned set is iron plate (Smith, the default). Its explosives are spells, not items.
    ('_pike', 'leather'), ('artificers:peasant_', 'leather'),
    ('_rapier', 'plate'),
    ('rogues:rogue_armor', 'leather'), ('rogues:assassin_armor', 'leather'),
    ('rogues:netherite_assassin_armor', 'leather'), ('armory_rpgs:deathmantle', 'leather'),
    ('_dagger', 'leather'), ('_sickle', 'leather'),
    ('archers:', 'leather'), ('archers_expansion:', 'leather'),
]
# Quivers are not RPG Series tiered gear; the small quiver stays free.
EXTRA_GEAR = {('tier_1', 'leather'): ['archers:medium_quiver'], ('tier_2', 'leather'): ['archers:large_quiver']}
GEAR_TIERS = [
    # tier key, required level, title, icon per group
    ('tier_1', 10, 'tier 1', {'caster': 'wizards:staff_wizard', 'plate': 'paladins:iron_claymore', 'leather': 'archers:composite_longbow'}),
    ('tier_2', 20, 'tier 2 (diamond)', {'caster': 'wizards:staff_arcane', 'plate': 'paladins:diamond_claymore', 'leather': 'archers:royal_longbow'}),
    ('tier_3', 25, 'tier 3 (netherite)', {'caster': 'wizards:staff_netherite_arcane', 'plate': 'paladins:netherite_claymore', 'leather': 'archers:netherite_longbow'}),
    ('set', 30, 'Armory set', {'caster': 'armory_rpgs:astral_robe_chest', 'plate': 'armory_rpgs:destroyer_armor_chest', 'leather': 'archers_expansion:bounty_hunter_chest'}),
]

# Enchanter: Apothic Enchanting shelves by the enchanting power they unlock (max Eterna).
# Plain bookshelves (max 15 = vanilla level 30 enchants) stay free for everyone. Infused shelves
# (infused hell/seashelf, deepshelf) are made in the enchanting table, which Item Restrictions
# can't see; they are gated through their gated inputs (hellshelf, seashelf, dormant deepshelf).
ENCHANTER_GATES = [
    ('enchanter_shelf_1', 10, 'Hellshelf and Seashelf (power 45)',
     ['apothic_enchanting:hellshelf', 'apothic_enchanting:seashelf'], 'apothic_enchanting:hellshelf'),
    ('enchanter_shelf_2', 20, 'Glowing, Blazing, Crystal and Heart shelves (power 60-65)',
     ['apothic_enchanting:glowing_hellshelf', 'apothic_enchanting:blazing_hellshelf',
      'apothic_enchanting:crystal_seashelf', 'apothic_enchanting:heart_seashelf'], 'apothic_enchanting:blazing_hellshelf'),
    ('enchanter_shelf_3', 25, 'Deep and Sculk shelves (power 70-80)',
     ['apothic_enchanting:dormant_deepshelf', 'apothic_enchanting:echoing_deepshelf',
      'apothic_enchanting:soul_touched_deepshelf', 'apothic_enchanting:echoing_sculkshelf',
      'apothic_enchanting:soul_touched_sculkshelf'], 'apothic_enchanting:echoing_sculkshelf'),
    ('enchanter_shelf_4', 30, 'Endshelves (power 90-100)',
     ['apothic_enchanting:endshelf', 'apothic_enchanting:pearl_endshelf',
      'apothic_enchanting:draconic_endshelf'], 'apothic_enchanting:draconic_endshelf'),
]

# Alchemist: brewing stronger potions. One restriction file per potion so that Jobs+ shows the
# requirement tooltip on each potion and lists each one in its Jobs menu (it only reads
# top-level item conditions).
ALCHEMIST_STRONG_LEVEL = 10
STRONG_POTIONS = [
    'strong_harming', 'strong_healing', 'strong_leaping', 'strong_poison', 'strong_regeneration',
    'strong_slowness', 'strong_strength', 'strong_swiftness', 'strong_turtle_master',
    'long_fire_resistance', 'long_invisibility', 'long_leaping', 'long_night_vision', 'long_poison',
    'long_regeneration', 'long_slow_falling', 'long_slowness', 'long_strength', 'long_swiftness',
    'long_turtle_master', 'long_water_breathing', 'long_weakness',
]
ALCHEMIST_THROWABLE = [
    ('alchemist_splash', 15, 'minecraft:splash_potion'),
    ('alchemist_lingering', 20, 'minecraft:lingering_potion'),
]

# --------------------------------------------------------------------------------------
# Extra job XP (Arc actions; KubeJS covers what Arc can't see, see minerpg_jobs.js)
# --------------------------------------------------------------------------------------
# Bonus on top of the default "craft tools/armor" 2-4 XP when a gated item is crafted.
CRAFT_BONUS = {
    'tier_1': (8, 12), 'tier_2': (15, 20), 'tier_3': (25, 30), 'set': (40, 50),
    'enchanter_shelf_1': (10, 12), 'enchanter_shelf_2': (15, 20), 'enchanter_shelf_3': (20, 25),
    'enchanter_shelf_4': (30, 35),
}
# Brewing a gated potion: bonus per bottle on top of the default 1-2.
BREW_BONUS = (3, 4)
# Alchemist: runes (Rune Crafting Altar and hand recipes) and Apotheosis potion charms.
RUNE_XP = (4, 6)
CHARM_XP = (20, 30)

# Hunter = Skinning + Leatherworking (designer revision). Jobs+'s default Hunter action pays
# 4-6 XP for killing *any* mob; it is replaced (same id, data/jobsplus/arc/hunter/kill_mob.json)
# by one that pays only for animals hunted for hides and meat. Monster kills pay through
# skinning instead (kubejs/server_scripts/minerpg_jobs.js: XP per hide/bone/monster part dropped).
HUNTED_ANIMALS = ['minecraft:cow', 'minecraft:mooshroom', 'minecraft:pig', 'minecraft:sheep', 'minecraft:chicken',
                  'minecraft:rabbit', 'minecraft:horse', 'minecraft:donkey', 'minecraft:mule', 'minecraft:llama',
                  'minecraft:trader_llama', 'minecraft:goat', 'minecraft:hoglin', 'minecraft:polar_bear',
                  'minecraft:fox', 'minecraft:camel', 'minecraft:armadillo', 'minecraft:turtle']
ANIMAL_KILL_XP = (3, 5)
# Leatherworking: crafting leather goods (on top of the gated-gear bonus above).
LEATHER_GOODS = ['minecraft:leather', 'minecraft:leather_helmet', 'minecraft:leather_chestplate',
                 'minecraft:leather_leggings', 'minecraft:leather_boots', 'minecraft:leather_horse_armor',
                 'minecraft:saddle', 'minecraft:bundle', 'minecraft:item_frame', 'archers:small_quiver']
LEATHER_XP = (3, 5)

# Job level milestones for the quest book ("reach level N in any job").
MILESTONES = [10, 20, 30]
JOBS = ['alchemist', 'builder', 'digger', 'enchanter', 'farmer', 'fisherman', 'hunter',
        'lumberjack', 'miner', 'smith']

# Repeatable advancements: KubeJS gives job XP and revokes them so they fire again.
XP_ADVANCEMENTS = {
    'spell_bind': {'bind': {'trigger': 'spell_engine:spell_binding', 'conditions': {}}},
    'spell_book': {'book': {'trigger': 'spell_engine:spell_book_creation', 'conditions': {}}},
    'socket_gem': {'socket': {'trigger': 'minecraft:recipe_crafted', 'conditions': {'recipe_id': 'apotheosis:socketing'}}},
    'add_socket': {'sigil': {'trigger': 'minecraft:recipe_crafted', 'conditions': {'recipe_id': 'apotheosis:sigil_add_sockets'}}},
}

SILENT_GRANT = 'minerpg_jobs grant %player% '  # KubeJS command, no chat feedback


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def reset(path):
    if os.path.isdir(path):
        shutil.rmtree(path)


def holder(job):
    return {'type': 'jobsplus:job', 'id': f'jobsplus:{job}'}


def job_exp(lo, hi):
    return {'type': 'jobsplus:job_exp', 'chance': 100, 'min': lo, 'max': hi}


def potion_stack(item, potion=None):
    s = {'id': item, 'count': 1}
    if potion:
        s['components'] = {'minecraft:potion_contents': {'potion': potion}}
    return s


def gear_groups(server):
    """Class gear by (tier, group) -> sorted item ids, from the installed jars and tag cache."""
    mods = os.path.join(server, 'mods')
    cache = json.load(open(os.path.join(server, 'config', 'rpg_series', 'tag_cache.json')))['cache']
    jar_tags = {}
    for jar in glob.glob(os.path.join(mods, '*.jar')):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.startswith('data/rpg_series/tags/item/armor_type/') and name.endswith('.json'):
                    key = 'armor_type/' + name.split('/')[-1][:-5]
                    for v in json.loads(z.read(name)).get('values', []):
                        jar_tags.setdefault(key, set()).add(v if isinstance(v, str) else v['id'])
    def members(tag):
        return set(cache.get('rpg_series:' + tag, [])) | jar_tags.get(tag, set())
    caster = members('armor_type/magic') | members('archetype/magic_damage_weapon') | members('archetype/healing_weapon')
    ranged = members('armor_type/archery') | members('archetype/ranged_damage_weapon')

    def group(item):
        for part, g in GEAR_GROUP_OVERRIDES:
            if part in item:
                return g
        if item in caster:
            return 'caster'
        if item in ranged:
            return 'leather'
        return 'plate'  # melee/defense weapons, melee armor, and anything untagged

    tiers = {
        'tier_1': cache['rpg_series:loot_tier/tier_1_weapons'] + cache['rpg_series:loot_tier/tier_1_armors'],
        'tier_2': cache['rpg_series:loot_tier/tier_2_weapons'] + cache['rpg_series:loot_tier/tier_2_armors'],
        'tier_3': cache['rpg_series:loot_tier/tier_3_weapons'] + cache['rpg_series:loot_tier/tier_3_armors'],
        'set': armory_items(mods),
    }
    out = {}
    for key, items in EXTRA_GEAR.items():
        out[key] = list(items)
    for tier, items in tiers.items():
        for item in sorted(set(items)):
            out.setdefault((tier, group(item)), []).append(item)
    return out


def armory_items(mods):
    """Smithing results that take an upgrade crystal (Armory, More RPG Classes sets)."""
    found = set()
    for jar in glob.glob(os.path.join(mods, '*.jar')):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if '/recipe/' not in name or not name.endswith('.json'):
                    continue
                try:
                    d = json.loads(z.read(name))
                except (ValueError, UnicodeDecodeError):
                    continue
                if d.get('type') != 'minecraft:smithing_transform':
                    continue
                if 'upgrade_crystal' in json.dumps(d.get('addition')) or 'epic_armor_upgrade' in json.dumps(d.get('template')):
                    found.add(d['result']['id'])
    return sorted(found)


def restriction(job, level, types, item_condition, icon):
    return {
        'icon': icon,
        'types': types,
        'conditions': [
            item_condition,
            # Restricted while the player's level in this job is below `level` (no job = level 0).
            # The job must be named: Item Restrictions checks have no job "source".
            {'type': 'jobsplus:job_level', 'job': f'jobsplus:{job}', 'level': level, 'inverted': True},
        ],
    }


def build(server):
    tag_dir = os.path.join(PACK, 'tags', 'item', 'job_gate')
    gear = gear_groups(server)
    if not any(k[0] == 'set' for k in gear):
        raise SystemExit('no Armory set items found')

    for path in [os.path.join(PACK, 'itemrestrictions'), tag_dir, os.path.join(PACK, 'arc', 'gen'),
                 os.path.join(PACK, 'advancement', 'jobs_xp')]:
        reset(path)

    restrictions = os.path.join(PACK, 'itemrestrictions', 'restrictions')
    arc = os.path.join(PACK, 'arc', 'gen')
    count = 0

    # Crafting gates (class gear by group and tier, Enchanter shelves) + crafting XP bonus.
    gates = []
    for tier, level, title, icons in GEAR_TIERS:
        for grp, job in GEAR_GROUP_JOB.items():
            items = gear.get((tier, grp))
            if items:
                gates.append((job, f'gear_{grp}_{tier}', level, items, icons[grp], CRAFT_BONUS[tier]))
    for key, level, title, items, icon in ENCHANTER_GATES:
        gates.append(('enchanter', key, level, items, icon, CRAFT_BONUS[key]))
    for job, key, level, values, icon, bonus in gates:
        write(os.path.join(tag_dir, key + '.json'), {
            'replace': False, 'values': [{'id': v, 'required': False} for v in values]})
        items = {'type': 'arc:items', 'items': [f'#minerpg:job_gate/{key}']}
        write(os.path.join(restrictions, key + '.json'),
              restriction(job, level, ['craft'], items, {'id': icon, 'count': 1}))
        count += 1
        lo, hi = bonus
        write(os.path.join(arc, job, f'craft_{key}.json'), {
            'holder': holder(job),
            'type': 'arc:on_craft_item',
            'rewards': [job_exp(lo, hi),
                        {'type': 'arc:command', 'command': SILENT_GRANT + 'minerpg:jobs/gated_craft'}],
            'conditions': [items],
        })

    # Brewing gates (Alchemist) + brewing XP bonus.
    gated_potions = []
    for potion in STRONG_POTIONS:
        cond = {'type': 'arc:item', 'item': potion_stack('minecraft:potion', 'minecraft:' + potion)}
        gated_potions.append(cond)
        write(os.path.join(restrictions, f'alchemist_{potion}.json'),
              restriction('alchemist', ALCHEMIST_STRONG_LEVEL, ['brew'], cond, potion_stack('minecraft:potion', 'minecraft:' + potion)))
        count += 1
    for key, level, item in ALCHEMIST_THROWABLE:
        cond = {'type': 'arc:items', 'items': [item]}
        gated_potions.append(cond)
        write(os.path.join(restrictions, key + '.json'),
              restriction('alchemist', level, ['brew'], cond, potion_stack(item, 'minecraft:healing')))
        count += 1
    write(os.path.join(arc, 'alchemist', 'brew_gated_potion.json'), {
        'holder': holder('alchemist'),
        'type': 'arc:on_brew_potion',
        'rewards': [job_exp(*BREW_BONUS), {'type': 'arc:command', 'command': SILENT_GRANT + 'minerpg:jobs/gated_craft'}],
        'conditions': [{'type': 'arc:or', 'conditions': gated_potions}],
    })
    # Runes (any recipe that makes a rune: Rune Crafting Altar or crafting table).
    write(os.path.join(arc, 'alchemist', 'craft_runes.json'), {
        'holder': holder('alchemist'),
        'type': 'arc:on_craft_item',
        'rewards': [job_exp(*RUNE_XP)],
        'conditions': [{'type': 'arc:items', 'items': ['#runes:runes']}],
    })
    write(os.path.join(arc, 'alchemist', 'craft_potion_charm.json'), {
        'holder': holder('alchemist'),
        'type': 'arc:on_craft_item',
        'rewards': [job_exp(*CHARM_XP)],
        'conditions': [{'type': 'arc:items', 'items': ['apotheosis:potion_charm']}],
    })

    # Hunter: animals-only kill XP (replaces the Jobs+ default) and leatherworking.
    write(os.path.join(ROOT, 'config', 'originpacks', 'minerpg_jobs', 'data', 'jobsplus', 'arc', 'hunter', 'kill_mob.json'), {
        'holder': holder('hunter'),
        'type': 'arc:on_kill_entity',
        'rewards': [job_exp(*ANIMAL_KILL_XP)],
        'conditions': [{'type': 'arc:entity_types', 'entity_types': HUNTED_ANIMALS}],
    })
    write(os.path.join(arc, 'hunter', 'craft_leather_goods.json'), {
        'holder': holder('hunter'),
        'type': 'arc:on_craft_item',
        'rewards': [job_exp(*LEATHER_XP)],
        'conditions': [{'type': 'arc:items', 'items': LEATHER_GOODS}],
    })

    # Level milestones (quest book): any job reaching N grants minerpg:jobs/level_N.
    for job in JOBS:
        for level in MILESTONES:
            write(os.path.join(arc, 'milestone', f'{job}_{level}.json'), {
                'holder': holder(job),
                'type': 'jobsplus:on_job_level_up',
                'rewards': [{'type': 'arc:command', 'command': SILENT_GRANT + f'minerpg:jobs/level_{level}'}],
                'conditions': [{'type': 'jobsplus:job_level', 'job': f'jobsplus:{job}', 'level': level}],
            })

    for key, criteria in XP_ADVANCEMENTS.items():
        write(os.path.join(PACK, 'advancement', 'jobs_xp', key + '.json'), {'criteria': criteria})

    print(f'{count} item restrictions, ' + ', '.join(f'{k[1]} {k[0]}: {len(v)}' for k, v in sorted(gear.items())) + ', '
          f'{len(JOBS) * len(MILESTONES)} milestone actions, {len(XP_ADVANCEMENTS)} XP advancements')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
