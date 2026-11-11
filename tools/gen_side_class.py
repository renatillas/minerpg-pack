#!/usr/bin/env python3
"""The Side Class talent tab (pack 1.7.0): pack/kubejs/data/minerpg/puffish_skills/.

  python3 pack/tools/gen_side_class.py <mods dir>      (dist/server/mods, or the scratch server's)

Design: docs/superpowers/specs/2026-11-08-minerpg-side-class-design.md. A second Pufferfish category,
minerpg:side_skills, holds one small tree per class: its root, its first 4 tome spells (two tier-2, two tier-3)
granted as spells, the main tree's 2 upgrades for each, and its 4 tier-1/2 passives. 8 points, own XP bar.

Source: the class tree that gen_mastery.py extracts to pack/kubejs/mastery/class_skills/ (positions,
definitions, rewards) and the tree's spell files in the mods (each "tier_N_spell_K_root" is a Spell Engine modifier
whose spell_pattern names the tome spell it belongs to). No mod ships the minerpg namespace, so this is plain data
(the main tree needs KubeJS' generateData('last'); this one doesn't).

Rules data can't express: 2 of the 4 spells and side class != main class are in
kubejs/startup_scripts/minerpg_side_class.js (reads pack/kubejs/side_class/rules.json, written here); the 9-point gate
is in kubejs/server_scripts/minerpg_side_class.js. rules.json keys the main tree's roots by their skill ids, so rerun
this whenever gen_mastery.py or a class-tree mod update changes the main tree.
"""

import glob
import json
import os
import re
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN = os.path.join(ROOT, 'kubejs', 'mastery', 'class_skills')
MAIN_CATEGORY = os.path.join(ROOT, 'kubejs', 'data', 'skill_tree_rpgs', 'puffish_skills', 'categories', 'class_skills')
OUT = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'puffish_skills')
RULES = os.path.join(ROOT, 'kubejs', 'side_class', 'rules.json')

POINTS = 8
LEVEL_COST = '3000 + level * 600'
# (side node suffix, main tree definition suffix): the four spells, in the order tier 2 spell 1, 2, tier 3 spell 1, 2.
SPELL_SLOTS = [('spell_1', 'tier_2_spell_1'), ('spell_2', 'tier_2_spell_2'),
               ('spell_3', 'tier_3_spell_1'), ('spell_4', 'tier_3_spell_2')]
PASSIVES = [('passive_1', 'tier_1_passive_1'), ('passive_2', 'tier_1_passive_2'),
            ('passive_3', 'tier_2_passive_1'), ('passive_4', 'tier_2_passive_2')]


def load(name):
    with open(os.path.join(MAIN, name + '.json')) as f:
        return json.load(f)


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1)
        f.write('\n')


def mod_files(mods):
    """Installed mod ids, and every data/*/spell/*.json in the mods by spell id."""
    mod_ids, spells, books = set(), {}, {}
    for jar in glob.glob(os.path.join(mods, '*.jar')):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name == 'META-INF/neoforge.mods.toml':
                    mod_ids.update(re.findall(r'modId\s*=\s*"([^"]+)"', z.read(name).decode('utf-8', 'replace')))
                b = re.match(r'data/([^/]+)/tags/spell/spell_book/([^/]+)\.json$', name)
                if b:
                    try:
                        books[f'{b.group(1)}:{b.group(2)}'] = json.loads(z.read(name)).get('values', [])
                    except ValueError:
                        pass
                m = re.match(r'data/([^/]+)/spell/([^/]+)\.json$', name)
                if m:
                    try:
                        spells[f'{m.group(1)}:{m.group(2)}'] = json.loads(z.read(name))
                    except ValueError:
                        pass
    tomes = set()
    for values in books.values():
        tomes.update(v['id'] if isinstance(v, dict) else v for v in values)
    return mod_ids, spells, {t for t in tomes if not t.startswith('#')}


def reward_spell(definition):
    """The (single) spell id a main tree node grants."""
    return definition['rewards'][0]['data']['containers'][0]['spell_ids'][0]


def tome_spell(tree_spells, tomes, node_ids):
    """The tome spell a main tree spell slot belongs to: the first spell the slot's root modifier or its two upgrades
    point at (modifier spell_pattern, or a passive trigger's spell id) that a class tome teaches. Some point at a
    helper spell instead (elemental_wizards_rpg:helper/wind_twister_impact), so the tome spell whose name is part of
    that id counts too."""
    refs = []
    for node_id in node_ids:
        spell = tree_spells.get(node_id, {})
        refs += [m.get('spell_pattern', '') for m in spell.get('modifiers', [])]
        refs += [t.get('spell', {}).get('id', '') for t in spell.get('passive', {}).get('triggers', [])]
    for ref in refs:
        if ref in tomes:
            return ref
    for ref in refs:
        if ':' not in ref:
            continue
        found = sorted(t for t in tomes
                       if t.split(':')[0] == ref.split(':')[0] and t.split(':')[1] in ref.split(':')[1])
        if len(found) > 1:
            raise SystemExit(f'{ref}: more than one tome spell matches ({", ".join(found)}); pick one by hand')
        if found:
            return found[0]
    return None


def spell_reward(spell_ids):
    return {'type': 'skill_tree_rpgs:spell', 'data': {'containers': [{
        'access': 'NONE', 'access_param': '', 'extra_tier_binding': 0, 'max_spell_count': 0, 'pool': '', 'slot': '',
        'spell_ids': spell_ids}]}}


def build(mods):
    definitions, skills_main = load('definitions'), load('skills')
    mod_ids, spells, tomes = mod_files(mods)
    by_def = {v['definition']: (k, v) for k, v in skills_main.items()}
    classes = sorted(d[:-len('_root')] for d in by_def if d.endswith('_root') and by_def[d][1].get('root'))

    defs, skills, links, rules = {}, {}, [], {'spells': {}, 'main_roots': {}, 'side_roots': {}}
    for cls in classes:
        root_def = definitions[f'{cls}_root']
        if not set(root_def.get('required_mods', [])) <= mod_ids:
            continue  # the Witcher trees: their mod isn't in the pack
        main_root_id = by_def[f'{cls}_root'][0]
        rules['main_roots'][main_root_id] = cls

        def sid_for(cls_, suffix_):
            return f'side_{cls_}_{suffix_}'

        def node(suffix, main_def, definition=None):
            sid = f'side_{cls}_{suffix}'
            pos = by_def[main_def][1]
            defs[sid] = definition if definition is not None else definitions[main_def]
            skills[sid] = {'definition': sid, 'x': pos['x'], 'y': pos['y']}
            return sid

        root = node('root', f'{cls}_root')
        skills[root]['root'] = True
        rules['side_roots'][root] = cls
        rules['spells'][cls] = []
        for suffix, slot in SPELL_SLOTS:
            modifier_id = reward_spell(definitions[f'{cls}_{slot}_root'])
            tome = tome_spell(spells, tomes, [modifier_id] + [
                reward_spell(definitions[f'{cls}_{slot}_modifier_{up}']) for up in (1, 2)])
            if tome is None or tome not in spells:
                raise SystemExit(f'{cls} {slot}: no tome spell found')
            ns, path = tome.split(':')
            spell = node(suffix, f'{cls}_{slot}_root', {
                'title': {'translate': f'spell.{ns}.{path}.name'},
                # Filled in on the client by kubejs/client_scripts/minerpg_side_class_tooltips.js (the class tree's own
                # tooltip list only knows its own skills): the tome spell's card, the bonus upgrade, the 2-of-4 rule.
                'description': {'skill_definition_id': sid_for(cls, suffix)},
                'icon': {'type': 'texture', 'data': {'texture': f'{ns}:textures/spell/{path}.png'}},
                # The tome spell itself, plus the main tree's own upgrade on this node.
                'rewards': [spell_reward([tome, modifier_id])],
            })
            rules['spells'][cls].append(spell)
            links.append([root, spell])
            for up in (1, 2):
                links.append([spell, node(f'{suffix}_up_{up}', f'{cls}_{slot}_modifier_{up}')])
        p1, p2, p3, p4 = (node(suffix, f'{cls}_{main}') for suffix, main in PASSIVES)
        links += [[root, p1], [root, p2], [p1, p3], [p2, p4]]
    return defs, skills, {'normal': {'bidirectional': links}, 'exclusive': {'bidirectional': []}}, rules


def check(defs, skills, connections, rules):
    errors = []
    classes = rules['spells']
    if len(classes) != 17:
        errors.append(f'{len(classes)} classes, expected 17')
    links = connections['normal']['bidirectional']
    neighbours = {}
    for a, b in links:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    for cls, spell_ids in classes.items():
        own = [s for s in skills if s.startswith(f'side_{cls}_')]
        if len(own) != 17:
            errors.append(f'{cls}: {len(own)} skills, expected 17')
        root = f'side_{cls}_root'
        for n, spell in enumerate(spell_ids, 1):
            ids = defs[spell]['rewards'][0]['data']['containers'][0]['spell_ids']
            if len(ids) != 2 or not ids[1].endswith('_root'):
                errors.append(f'{spell}: rewards {ids}')
            if root not in neighbours.get(spell, ()):
                errors.append(f'{spell}: not connected from the root')
            for up in (1, 2):
                if neighbours.get(f'{spell}_up_{up}') != {spell}:
                    errors.append(f'{spell}_up_{up}: must hang off its spell only')
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    defs, skills, connections, rules = build(sys.argv[1])
    check(defs, skills, connections, rules)
    with open(os.path.join(MAIN_CATEGORY, 'category.json')) as f:
        category = json.load(f)
    category.update({'title': 'Side Class', 'unlocked_by_default': False, 'spent_points_limit': POINTS,
                     'exclusive_root': True})
    with open(os.path.join(MAIN_CATEGORY, 'experience.json')) as f:
        experience = json.load(f)
    experience['level_limit'] = POINTS
    experience['experience_per_level'] = {'type': 'expression', 'data': {'expression': LEVEL_COST}}
    base = os.path.join(OUT, 'categories', 'side_skills')
    # OUT/config.json lists the minerpg categories (side_skills, ascension); it is hand-maintained.
    write(os.path.join(base, 'category.json'), category)
    write(os.path.join(base, 'experience.json'), experience)
    write(os.path.join(base, 'definitions.json'), defs)
    write(os.path.join(base, 'skills.json'), skills)
    write(os.path.join(base, 'connections.json'), connections)
    write(RULES, rules)
    print(f'{len(rules["spells"])} classes, {len(skills)} skills -> {base}')


if __name__ == '__main__':
    main()
