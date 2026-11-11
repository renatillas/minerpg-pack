#!/usr/bin/env python3
"""Extract the class skill tree (Skill Tree RPGs + More RPG Classes) into pack/kubejs/mastery/class_skills/.

The Mastery tier this script used to add (pack 1.5.2) was removed in 1.8.0 for Ascension
(docs/superpowers/specs/2026-11-11-minerpg-ascension-design.md). The extracted tree is the source that
gen_side_class.py builds the Side Class tab from; nothing in the pack overrides the class tree any more.

Run:  python3 pack/tools/gen_mastery.py <server dir>    (the server's mods/ holds the jars)
Writes: pack/kubejs/mastery/class_skills/{skills,definitions,connections}.json
"""
import glob
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
TREES = os.path.join(ROOT, 'kubejs', 'mastery', 'class_skills')
TREE_PATH = 'resourcepacks/mrpgc_skill_tree_changes/data/skill_tree_rpgs/puffish_skills/categories/class_skills/'


def read_tree(server):
    for jar in glob.glob(os.path.join(server, 'mods', 'mrpgc_skill_tree-*.jar')):
        with zipfile.ZipFile(jar) as z:
            return {n: json.loads(z.read(TREE_PATH + n + '.json')) for n in ('skills', 'definitions', 'connections')}
    raise SystemExit('More RPG Classes skill tree jar not found')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    tree = read_tree(sys.argv[1])
    skills, defs, conns = tree['skills'], tree['definitions'], tree['connections']
    os.makedirs(TREES, exist_ok=True)
    leftover = sorted(d for d in defs if 'mastery' in d)
    if leftover:
        raise SystemExit(f'Mastery was removed in 1.8.0, but the tree still has: {", ".join(leftover[:5])} ...')
    for name, obj in (('skills', skills), ('definitions', defs), ('connections', conns)):
        with open(os.path.join(TREES, name + '.json'), 'w') as f:
            json.dump(obj, f, separators=(',', ':'))
    print(f'{len(skills)} class tree skills -> {TREES}')


if __name__ == '__main__':
    main()
