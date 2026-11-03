#!/usr/bin/env python3
"""Generate Apotheosis salvaging recipes for RPG Series gear, jewelry and relics.

Design: docs/superpowers/specs/2026-11-03-minerpg-recycling-design.md.

The Salvaging Table only knows vanilla tools and armor (their materials), items with a rarity (rarity
materials) and gems (gem dust). This script adds a recipe for every crafted RPG weapon, shield, quiver,
armor piece and jewel, giving back part of its main material at Apotheosis' own vanilla rates, and for
every relic and unique jewel, giving rarity materials. An item with a rarity still also gives its rarity
material (Apotheosis adds up every matching recipe). Unique weapons get no recipe: they always have a
rarity (kubejs/server_scripts/minerpg_salvage.js).

Recipes are read from the mod jars, so they follow the mods' own recipes when the mods update.

Run:  python3 pack/tools/gen_salvage.py <server dir>    (the server's mods/ holds the jars)
Writes: pack/kubejs/data/minerpg/recipe/salvaging/rpg/<ns>__<item>.json (the folder is replaced)
"""
import glob
import json
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
OUT = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'recipe', 'salvaging', 'rpg')

GEAR_NS = {'wizards', 'paladins', 'rogues', 'archers', 'archers_expansion', 'armory_rpgs', 'arsenal',
           'bards_rpg', 'berserker_rpg', 'forcemaster_rpg', 'elemental_wizards_rpg'}
JEWELRY_NS = {'jewelry', 'additional_rpg_jewelry'}
RELIC_NS = {'relics_rpgs', 'more_relics'}
ALL_NS = GEAR_NS | JEWELRY_NS | RELIC_NS

# Never recyclable, though they have recipes: blocks, progression items (spell books/scrolls, upgrade
# crystals and song sheets are not crafted at a crafting table, so they never come up).
EXCLUDE = re.compile(r'(_workbench|jewelers_kit|socket_mount|music_stand|epic_armor_upgrade|upgrade_crystal|'
                     r'elemental_essence)$')

# Rarity materials (Apotheosis' own salvage outputs).
RARITY_MATERIAL = {
    'uncommon': 'apotheosis:timeworn_fabric', 'rare': 'apotheosis:luminous_crystal_shard',
    'epic': 'apotheosis:arcane_sands', 'mythic': 'apotheosis:godforged_pearl',
}
RELIC_GRADE = {'lesser': 'uncommon', 'medium': 'rare', 'greater': 'epic', 'superior': 'mythic'}

GEMS = {'minecraft:diamond', 'minecraft:emerald', 'jewelry:ruby', 'jewelry:sapphire', 'jewelry:topaz',
        'jewelry:citrine', 'jewelry:jade', 'jewelry:tanzanite', 'additional_rpg_jewelry:aquamarine',
        'additional_rpg_jewelry:malachite'}
METALS = ['minecraft:netherite_ingot', 'minecraft:gold_ingot', 'minecraft:iron_ingot', 'minecraft:copper_ingot']
# Main material = the most valuable ingredient. Anything not listed is worth 10.
VALUE = {'minecraft:netherite_ingot': 100, 'minecraft:netherite_scrap': 90, 'minecraft:diamond': 80,
         'minecraft:emerald': 70, 'minecraft:gold_ingot': 50, 'minecraft:ghast_tear': 45,
         'minecraft:iron_ingot': 40, 'minecraft:chain': 35, 'minecraft:copper_ingot': 30,
         'minecraft:amethyst_shard': 30, 'minecraft:blaze_powder': 25, 'minecraft:prismarine_shard': 25,
         'minecraft:ender_pearl': 25, 'minecraft:lapis_lazuli': 20, 'minecraft:leather': 20,
         'mrpg_lib:hardened_leather': 20, 'minecraft:rabbit_hide': 15, 'minecraft:white_wool': 15}
VALUE.update({g: 60 for g in GEMS if g not in VALUE})
NEVER_OUTPUT = {'minecraft:stick', 'minecraft:netherite_upgrade_smithing_template', 'minecraft:gold_nugget',
                'minecraft:iron_nugget'}
# Vanilla item tags (not in the mod jars) -> the item given back.
VANILLA_TAGS = {'minecraft:wool': 'minecraft:white_wool', 'minecraft:planks': 'minecraft:oak_planks',
                'minecraft:logs': 'minecraft:oak_log', 'minecraft:logs_that_burn': 'minecraft:oak_log',
                'minecraft:stone_tool_materials': 'minecraft:cobblestone'}
ARMOR = re.compile(r'_(head|chest|legs|feet)$')


def read_jars(server):
    """-> (recipes: list of recipe json, tags: {tag: [entries]}, items: set of item ids, mod ids)."""
    recipes, tags, items, mods = [], {}, set(), set()
    jars = glob.glob(os.path.join(server, 'mods', '*.jar'))
    for jar in jars:
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name == 'META-INF/neoforge.mods.toml':
                    mods.update(re.findall(r'modId\s*=\s*"([^"]+)"', z.read(name).decode('utf8', 'replace')))
    for jar in jars:
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                m = re.match(r'data/([^/]+)/(recipe|tags/item)/(.+)\.json$', name)
                lang = re.match(r'assets/([^/]+)/lang/en_us\.json$', name)
                if lang and lang.group(1) in ALL_NS:
                    for key in json.loads(z.read(name).decode('utf8', 'replace')):
                        k = re.match(r'item\.([^.]+)\.([^.]+)$', key)
                        if k and k.group(1) in ALL_NS:
                            items.add(f'{k.group(1)}:{k.group(2)}')
                if not m:
                    continue
                try:
                    data = json.loads(z.read(name).decode('utf8', 'replace'))
                except ValueError:
                    continue
                if m.group(2) == 'recipe':
                    recipes.append(data)
                else:
                    tags.setdefault(f'{m.group(1)}:{m.group(3)}', []).extend(data.get('values', []))
    return recipes, tags, items, mods


def loads(recipe, mods):
    """False when the recipe's NeoForge conditions need a mod that isn't installed."""
    for c in recipe.get('neoforge:conditions', []):
        if c.get('type') == 'neoforge:mod_loaded' and c.get('modid') not in mods:
            return False
    return True


def resolve(ingredient, tags):
    """An ingredient (item or tag) -> one item id, or None."""
    if isinstance(ingredient, list):
        ingredient = ingredient[0] if ingredient else {}
    if 'item' in ingredient:
        return ingredient['item']
    tag = ingredient.get('tag')
    if tag in VANILLA_TAGS:
        return VANILLA_TAGS[tag]
    for entry in tags.get(tag, []):
        entry = entry if isinstance(entry, str) else entry.get('id', '')
        if entry and not entry.startswith('#'):
            return entry
    return None


def output(item, lo, hi):
    return {'max_count': hi, 'min_count': lo, 'stack': {'count': 1, 'id': item}}


def crafted_outputs(result, recipe, tags, by_result, seen=()):
    """Salvage outputs for a crafted item, from its first recipe."""
    if recipe['type'] == 'minecraft:smithing_transform':
        addition = resolve(recipe.get('addition', {}), tags)
        if addition == 'minecraft:netherite_ingot':
            return [output('minecraft:netherite_scrap', 0, 2)]
        # Armory upgrades (an upgrade crystal on a class piece): the class piece's materials.
        base = resolve(recipe.get('base', {}), tags)
        if base in by_result and base not in seen:
            return crafted_outputs(base, by_result[base], tags, by_result, seen + (result,))
        return []
    ingredients = [resolve(i, tags) for i in recipe.get('key', {}).values()]
    ingredients = [i for i in ingredients if i and i not in NEVER_OUTPUT and (i in GEMS or i.split(':')[0] not in ALL_NS)]
    if not ingredients:
        return []
    ns = result.split(':')[0]
    if ns in JEWELRY_NS or 'jewel_figurine' in result:
        out = []
        metal = next((m for m in METALS if m in ingredients), None)
        if metal == 'minecraft:netherite_ingot':
            out.append(output('minecraft:netherite_scrap', 0, 1))
        elif metal:
            out.append(output(metal, 1, 2))
        gem = next((g for g in sorted(GEMS) if g in ingredients), None)
        if gem:
            out.append(output(gem, 0, 1))
        if out:
            return out
    def used(item):  # how many of this item the recipe takes
        return sum(''.join(recipe.get('pattern', [])).count(k) for k, v in recipe.get('key', {}).items()
                   if resolve(v, tags) == item)
    armor = ARMOR.search(result)
    # Weapons: the most valuable ingredient. Armor: value times amount (1 gold + 7 iron gives iron).
    main = max(ingredients, key=lambda i: VALUE.get(i, 10) * (min(used(i), 3) if armor else 1))
    if main == 'minecraft:netherite_ingot':
        return [output('minecraft:netherite_scrap', 0, 2)]
    if main in GEMS or not armor:
        return [output(main, 0, 1)]
    # Armor: 1-3, but always less than went in (2 scrap in boots must not give 3 back): 4+ -> 1-3,
    # 3 -> 1-2, 1-2 -> 0-1.
    hi = min(3, max(1, used(main) - 1))
    return [output(main, 1 if hi > 1 else 0, hi)]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    recipes, tags, items, mods = read_jars(sys.argv[1])
    by_result = {}
    for r in recipes:
        if r.get('type') not in ('minecraft:crafting_shaped', 'minecraft:crafting_shapeless',
                                 'minecraft:smithing_transform') or not loads(r, mods):
            continue
        res = r.get('result', {})
        rid = res.get('id') or res.get('item')
        if rid and rid.split(':')[0] in ALL_NS and rid not in by_result:
            by_result[rid] = r

    recipes_out = {}  # item id -> outputs
    skipped = []
    for item in sorted(items | set(by_result)):
        path = item.split(':')[1]
        if EXCLUDE.search(path):
            continue
        ns = item.split(':')[0]
        grade = path.split('_')[0]
        if ns in RELIC_NS and grade in RELIC_GRADE:
            out = [output(RARITY_MATERIAL[RELIC_GRADE[grade]], 1, 2)]
        elif item in by_result:
            out = crafted_outputs(item, by_result[item], tags, by_result)
        elif ns in JEWELRY_NS and re.search(r'_(ring|necklace)$', path):
            out = [output(RARITY_MATERIAL['epic'], 1, 2)]  # loot-only jewels (uniques, vampire...)
        else:
            out = []  # unique weapons (always have a rarity), song sheets, spell books and scrolls, gems
        if out:
            recipes_out[item] = out
        else:
            skipped.append(item)

    # One recipe per item, loaded only when the item exists: the jars name items for mods that aren't
    # installed (Aether, Better End... variants), and an unknown item would fail a shared recipe.
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for item, outs in recipes_out.items():
        recipe = {'neoforge:conditions': [{'type': 'neoforge:item_exists', 'item': item}],
                  'type': 'apotheosis:salvaging', 'input': [{'item': item}], 'outputs': outs}
        with open(os.path.join(OUT, item.replace(':', '__') + '.json'), 'w') as f:
            json.dump(recipe, f, indent=2)
            f.write('\n')
    print(f'{len(recipes_out)} recipes -> {OUT}')
    print(f'no recipe ({len(skipped)}): ' + ' '.join(skipped))


if __name__ == '__main__':
    main()
