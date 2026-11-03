#!/usr/bin/env python3
"""Generate the Mastery tiers: new class spells, passives and stat skills in the Skill Tree class trees.

Design: docs/superpowers/specs/2026-11-03-minerpg-mastery-tiers-design.md.

Each class in MASTERY gets 8 skills beyond tier 4: a new spell with two upgrades, a capstone passive, two passives
and two stat skills. The trees' skills/definitions/connections come from More RPG Classes' built-in datapack, which
loads after KubeJS's data folder, so the merged trees are written to kubejs/mastery/ and emitted at KubeJS's `last`
data stage by kubejs/server_scripts/minerpg_mastery.js.

Run:  python3 pack/tools/gen_mastery.py <server dir>    (the server's mods/ holds the jars)
Writes: pack/kubejs/data/minerpg/spell/mastery_*.json (folder entries replaced)
        pack/kubejs/mastery/class_skills/{skills,definitions,connections}.json
        pack/kubejs/assets/minerpg/textures/spell/mastery_*.png, lang keys in pack/kubejs/assets/minerpg/lang/en_us.json
"""
import glob
import json
import math
import os
import struct
import sys
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
SPELLS = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'spell')
TREES = os.path.join(ROOT, 'kubejs', 'mastery', 'class_skills')
ICONS = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'textures', 'spell')
LANG = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'lang', 'en_us.json')
TREE_PATH = 'resourcepacks/mrpgc_skill_tree_changes/data/skill_tree_rpgs/puffish_skills/categories/class_skills/'


# --------------------------------------------------------------------------------------
# Spell building blocks (Spell Engine 1.21 spell json)
# --------------------------------------------------------------------------------------
def particles(pid, count, color=None, shape='SPHERE', motion=None, lo=0.2, hi=0.5, anchor='ENTITY', **extra):
    appearance = {}
    if color is not None:
        appearance['color'] = color
    if motion:
        appearance['motion'] = motion
    batch = {'count': float(count), 'shape': shape, 'anchor': anchor, 'min_speed': lo, 'max_speed': hi}
    batch.update(extra)
    return {'id': pid, 'appearance': appearance, 'batch': batch}


def effect(effect_id, duration, amplifier=0, caster=False, **extra):
    se = {'effect_id': effect_id, 'duration': float(duration)}
    if amplifier:
        se['amplifier'] = amplifier
    se.update(extra)
    action = {'type': 'STATUS_EFFECT', 'status_effect': se}
    if caster:
        action['apply_to_caster'] = True
    return {'action': action}


def damage(coef, knockback=0.3, sound=None, parts=None):
    out = {'action': {'type': 'DAMAGE', 'damage': {'spell_power_coefficient': coef, 'knockback': knockback}}}
    if parts:
        out['visuals'] = {'particles': parts}
    if sound:
        out['sound'] = {'id': sound}
    return out


def heal(coef, parts=None, sound=None):
    out = {'action': {'type': 'HEAL', 'heal': {'spell_power_coefficient': coef}}}
    if parts:
        out['visuals'] = {'particles': parts}
    if sound:
        out['sound'] = {'id': sound}
    return out


def passive(school, triggers, impacts, cooldown=0.0, area=None, target='FROM_TRIGGER'):
    s = {'school': school, 'range': 0.0, 'tier': 1, 'type': 'PASSIVE', 'passive': {'triggers': triggers},
         'target': {'type': target}, 'impacts': impacts, 'cost': {'durability': 0}}
    if cooldown:
        s['cost']['cooldown'] = {'duration': cooldown}
    if area:
        s['area_impact'] = area
    return s


def modifier(school, pattern, **mods):
    return {'school': school, 'range': 0.0, 'tier': 1, 'type': 'MODIFIER',
            'modifiers': [dict({'spell_pattern': pattern}, **mods)]}


def append_impacts(*impacts):
    return {'mutate_impacts': 'APPEND', 'impacts': list(impacts)}


def area_impact(radius, parts, sound=None):
    a = {'radius': radius, 'area': {'distance_dropoff': 'SQUARED'}, 'visuals': {'particles': parts}}
    if sound:
        a['sound'] = {'id': sound}
    return a


def chance(trigger_type, p, **extra):
    t = {'type': trigger_type}
    if p < 1:
        t['chance'] = p
    t.update(extra)
    return t


def spell_hit(p, school=None, impact='DAMAGE', **extra):
    spell = {'type': 'ACTIVE'}
    if school:
        spell['school'] = school
    return chance('SPELL_IMPACT_SPECIFIC', p, spell=spell, impact={'impact_type': impact}, **extra)


GOLD, HOLY, FROST, BLOOD, GREEN = 4294954111, 4294954239, 3439329279, 4291559424, 4284940287

# --------------------------------------------------------------------------------------
# The Mastery designs. Spell ids: minerpg:mastery_<class>_<name>.
# Each class: (required mod, school, icon color, [skills]); a skill is
#   (key, kind, title, description, spell json or attribute reward, icon item for stats)
# kind: spell / upgrade / capstone / passive / stat
# --------------------------------------------------------------------------------------
def rogue():
    sch = 'spell_power:physical_melee'
    steel = 'minerpg:mastery_rogue_whirling_steel'
    return 'rogues', sch, (190, 190, 200), [
        ('whirling_steel', 'spell', 'Whirling Steel',
         'Spin and slash every enemy around you for {damage} damage, cracking their armor for {effect_duration} sec.',
         {'school': sch, 'range': 4.0, 'tier': 4, 'learn': {}, 'active': {},
          'release': {'animation': {'id': 'spell_engine:dual_handed_ground_release'},
                      'visuals': {'particles': [
                          particles('spell_engine:smoke_medium', 40, shape='CIRCLE', lo=0.25, hi=0.4, pre_travel=4.0),
                          particles('spell_engine:magic_spark', 40, color=4294967295, shape='CIRCLE', motion='DECELERATE',
                                    lo=0.4, hi=0.6)]},
                      'sound': {'id': 'rogues:shock_powder_release'}},
          'target': {'type': 'AREA', 'area': {'vertical_range_multiplier': 0.5}},
          'impacts': [damage(0.9, 0.5, 'rogues:shock_powder_impact'), effect('rogues:shatter', 6, 1)],
          'cost': {'exhaust': 0.3, 'cooldown': {'duration': 12.0}}}),
        ('wider_arc', 'upgrade', 'Wider Arc', 'Whirling Steel reaches {range_add} blocks further.',
         modifier(sch, steel, range_add=1.5)),
        ('hamstring', 'upgrade', 'Hamstring', 'Whirling Steel slows the enemies it hits for {effect_duration} sec.',
         modifier(sch, steel, **append_impacts(effect('minecraft:slowness', 3, 1)))),
        ('open_veins', 'capstone', 'Open Veins',
         'Melee hits have {trigger_chance} chance to make the target bleed for {effect_duration} sec.',
         passive(sch, [chance('MELEE_IMPACT', 0.2)],
                 [dict(effect('spell_engine:bleed', 5, 1, amplifier_power_multiplier=0.25),
                       visuals={'particles': [particles('spell_engine:dripping_blood', 20, lo=0.1, hi=0.3)]})],
                 cooldown=2.0)),
        ('footwork', 'passive', 'Footwork', 'After a dodge roll, you run faster for {effect_duration} sec.',
         passive(sch, [chance('ROLL', 1)], [effect('minecraft:speed', 3, 1, caster=True)], cooldown=1.0)),
        ('exploit_weakness', 'passive', 'Exploit Weakness',
         'Melee hits have {trigger_chance} chance to crack the target\'s armor for {effect_duration} sec.',
         passive(sch, [chance('MELEE_IMPACT', 0.15)], [effect('rogues:shatter', 5, 1)], cooldown=1.0)),
        ('quick_hands', 'stat', 'Quick Hands', None,
         ('minecraft:generic.attack_speed', 'multiply_base', 0.05), 'rogues:iron_dagger'),
        ('keen_edge', 'stat', 'Keen Edge', None,
         ('minecraft:generic.attack_damage', 'multiply_base', 0.05), 'rogues:iron_sickle'),
    ]


def frost():
    sch = 'spell_power:frost'
    field = 'minerpg:mastery_frost_rime_field'
    shard = [particles('spell_engine:frost_shard', 25, lo=0.3, hi=0.7),
             particles('spell_engine:snowflake', 25, lo=0.2, hi=0.5)]
    return 'wizards', sch, (120, 200, 255), [
        ('rime_field', 'spell', 'Rime Field',
         'Freezes the ground in front of you for {spawn_duration} sec. Enemies inside are slowed and take '
         '{damage} frost damage every second.',
         {'school': sch, 'range': 0.0, 'tier': 4, 'learn': {}, 'active': {
             'cast': {'duration': 0.5, 'animation': {'id': 'spell_engine:one_handed_area_charge'},
                      'sound': {'id': 'wizards:frost_nova_release'}}},
          'release': {'animation': {'id': 'spell_engine:one_handed_area_release'},
                      'sound': {'id': 'wizards:frost_nova_release'}},
          'deliver': {'type': 'CLOUD', 'clouds': [{
              'volume': {'radius': 3.0, 'area': {'vertical_range_multiplier': 1.0},
                         'sound': {'id': 'wizards:frost_nova_damage_impact'}},
              'time_to_live_seconds': 6.0, 'impact_tick_interval': 20,
              'placement': {'location_offset_by_look': 5.0, 'apply_yaw': True},
              'client_data': {'particles': [
                  particles('spell_engine:snowflake', 3, shape='PILLAR', lo=0.02, hi=0.2, vertical_origin=0.1, extent=3.0),
                  particles('spell_engine:frost_shard', 2, shape='PILLAR', lo=0.05, hi=0.25, vertical_origin=0.1,
                            extent=3.0)]},
              'spawn': {'sound': {'id': 'wizards:frost_nova_release'}}}]},
          'impacts': [damage(0.3, 0.0), effect('wizards:frost_slowness', 2, 1)],
          'cost': {'exhaust': 0.3, 'cooldown': {'duration': 16.0}}}),
        ('lingering_winter', 'upgrade', 'Lingering Winter', 'Rime Field lasts {spawn_duration_add} sec longer.',
         modifier(sch, field, spawn_duration_add=3.0)),
        ('spreading_rime', 'upgrade', 'Spreading Rime', 'Rime Field covers a wider area.',
         modifier(sch, field, cloud={'radius_add': 1.5})),
        ('splintering_cold', 'capstone', 'Splintering Cold',
         'Frost spell hits have {trigger_chance} chance to burst into shards, dealing {damage} frost damage to '
         'nearby enemies.',
         passive(sch, [spell_hit(0.25, 'frost')], [{'action': {'type': 'DAMAGE', 'allow_on_center_target': False,
                                                              'damage': {'spell_power_coefficient': 0.35, 'knockback': 0.2}}}],
                 cooldown=1.0, area=area_impact(2.5, shard, 'wizards:frost_nova_damage_impact'))),
        ('hoarfrost_retort', 'passive', 'Hoarfrost Retort',
         'When you are hit, {trigger_chance} chance to blast the attacker with cold, slowing it for '
         '{effect_duration} sec.',
         passive(sch, [chance('DAMAGE_TAKEN', 0.2)],
                 [dict(effect('wizards:frost_slowness', 3, 2), visuals={'particles': shard})], cooldown=6.0)),
        ('winters_grasp', 'passive', 'Winter\'s Grasp',
         'Frost spell hits have {trigger_chance} chance to slow the target heavily for {effect_duration} sec.',
         passive(sch, [spell_hit(0.2, 'frost')], [effect('minecraft:slowness', 3, 2)], cooldown=2.0)),
        ('deep_cold', 'stat', 'Deep Cold', None, ('spell_power:frost', 'multiply_base', 0.04), 'wizards:wand_frost'),
        ('quickened_frost', 'stat', 'Quickened Casting', None, ('spell_power:haste', 'multiply_base', 0.05),
         'wizards:staff_frost'),
    ]


def priest():
    sch = 'spell_power:healing'
    aegis = 'minerpg:mastery_priest_aegis_of_dawn'
    glow = [particles('spell_engine:magic_heal', 20, color=1728014079, shape='PILLAR', motion='ASCEND', lo=0.02,
                      hi=0.15, vertical_origin=0.1)]
    return 'paladins', sch, (255, 230, 150), [
        ('aegis_of_dawn', 'spell', 'Aegis of Dawn',
         'Shields you or an ally with a barrier that absorbs damage for {effect_duration} sec, and removes harmful '
         'effects.',
         {'school': sch, 'range': 16.0, 'tier': 4, 'learn': {}, 'active': {
             'cast': {'duration': 0.5, 'animation': {'id': 'spell_engine:one_handed_healing_charge'},
                      'sound': {'id': 'spell_engine:generic_healing_casting', 'randomness': 0.0}}},
          'release': {'animation': {'id': 'spell_engine:one_handed_healing_release'},
                      'sound': {'id': 'spell_engine:generic_healing_release', 'randomness': 0.0}},
          'target': {'type': 'AIM', 'aim': {'sticky': True, 'use_caster_as_fallback': True}},
          'impacts': [dict(effect('minecraft:absorption', 10, 1), visuals={'particles': glow},
                           sound={'id': 'spell_engine:generic_healing_impact_1'}),
                      {'action': {'type': 'STATUS_EFFECT', 'status_effect': {
                          'apply_mode': 'REMOVE', 'remove': {'id': '!minecraft:trial_omen'}}}}],
          'cost': {'exhaust': 0.2, 'cooldown': {'duration': 14.0}, 'item': {'id': 'runes:healing_stone'}}}),
        ('dawnlight', 'upgrade', 'Dawnlight', 'Aegis of Dawn also heals for {heal}.',
         modifier(sch, aegis, **append_impacts(heal(0.6)))),
        ('swift_aegis', 'upgrade', 'Swift Aegis', 'Aegis of Dawn cooldown reduced by {cooldown_duration_deduct} sec.',
         modifier(sch, aegis, cooldown_duration_deduct=4.0)),
        ('overflowing_grace', 'capstone', 'Overflowing Grace',
         'Your heals have {trigger_chance} chance to also heal everyone near the target for {heal}.',
         passive(sch, [spell_hit(0.25, impact='HEAL')], [heal(0.3)], cooldown=2.0,
                 area=area_impact(4.0, glow, 'spell_engine:generic_healing_impact_2'))),
        ('martyrs_resolve', 'passive', 'Martyr\'s Resolve', 'When you are hit, {trigger_chance} chance to heal '
         'yourself for {heal}.',
         passive(sch, [chance('DAMAGE_TAKEN', 0.15, target_override='CASTER')], [heal(0.4, glow)], cooldown=8.0)),
        ('radiant_rebuke', 'passive', 'Radiant Rebuke', 'Your holy damage has {trigger_chance} chance to heal allies '
         'around you for {heal}.',
         passive(sch, [spell_hit(0.2, 'healing', target_override='CASTER')], [heal(0.25)], cooldown=3.0,
                 area=area_impact(6.0, glow, 'spell_engine:generic_healing_impact_2'))),
        ('devotion', 'stat', 'Devotion', None, ('spell_power:healing', 'multiply_base', 0.04), 'paladins:holy_staff'),
        ('fortitude', 'stat', 'Fortitude', None, ('minecraft:generic.max_health', 'addition', 2.0),
         'minecraft:golden_apple'),
    ]


def deadeye():
    sch = 'spell_power:physical_ranged'
    mark = 'minerpg:mastery_deadeye_spotters_mark'
    return 'archers_expansion', sch, (230, 90, 70), [
        ('spotters_mark', 'spell', 'Spotter\'s Mark',
         'Marks an enemy for {effect_duration} sec: it glows for the whole party and its armor is cracked.',
         {'school': sch, 'range': 32.0, 'tier': 4, 'learn': {}, 'active': {},
          'release': {'animation': {'id': 'spell_engine:one_handed_projectile_release'},
                      'sound': {'id': 'spell_engine:generic_dispel_1'}},
          'target': {'type': 'AIM', 'aim': {'required': True}},
          'impacts': [dict(effect('minecraft:glowing', 10), visuals={'particles': [
              particles('spell_engine:magic_spark', 20, color=4294901760, shape='PILLAR', motion='ASCEND', lo=0.1,
                        hi=0.3, vertical_origin=0.1)]}),
              effect('rogues:shatter', 10, 1)],
          'cost': {'exhaust': 0.2, 'cooldown': {'duration': 18.0}}}),
        ('long_watch', 'upgrade', 'Long Watch', 'Spotter\'s Mark lasts {effect_duration_add} sec longer.',
         modifier(sch, mark, effect_duration_add=5.0)),
        ('pinned_quarry', 'upgrade', 'Pinned Quarry', 'Spotter\'s Mark also slows the target.',
         modifier(sch, mark, **append_impacts(effect('minecraft:slowness', 10, 1)))),
        ('second_arrow', 'capstone', 'Second Arrow',
         'Arrow hits have {trigger_chance} chance to strike the target again with a spectral bolt for {damage} '
         'damage.',
         passive(sch, [chance('ARROW_IMPACT', 0.2)],
                 [damage(0.5, 0.1, 'spell_engine:generic_dispel_1',
                         [particles('spell_engine:magic_spark', 20, color=4294967295, lo=0.2, hi=0.5)])],
                 cooldown=1.0)),
        ('quick_reflexes', 'passive', 'Quick Reflexes', 'After a dodge roll, you draw your bow faster for '
         '{effect_duration} sec.',
         passive(sch, [chance('ROLL', 1)], [effect('archers_expansion:fast_shot', 4, 0, caster=True)], cooldown=1.0)),
        ('headhunter', 'passive', 'Headhunter', 'Arrow hits have {trigger_chance} chance to stagger the target for '
         '{effect_duration} sec.',
         passive(sch, [chance('ARROW_IMPACT', 0.1)], [effect('minecraft:slowness', 1.5, 4)], cooldown=3.0)),
        ('steady_hands', 'stat', 'Steady Hands', None, ('ranged_weapon:damage', 'multiply_base', 0.04),
         'minecraft:bow'),
        ('hardened_hide', 'stat', 'Hardened Hide', None, ('minecraft:generic.armor', 'addition', 2.0),
         'minecraft:leather_chestplate'),
    ]


def paladin():
    sch = 'spell_power:healing'
    oath = 'minerpg:mastery_paladin_oathbound_aegis'
    holy = [particles('spell_engine:magic_holy', 20, color=HOLY, motion='DECELERATE', lo=0.2, hi=0.3)]
    return 'paladins', sch, (255, 210, 90), [
        ('oathbound_aegis', 'spell', 'Oathbound Aegis',
         'You and every ally within {range} blocks gain a barrier that absorbs damage and take less damage for '
         '{effect_duration} sec.',
         {'school': sch, 'range': 8.0, 'tier': 4, 'learn': {}, 'active': {
             'cast': {'duration': 0.5, 'animation': {'id': 'spell_engine:one_handed_area_charge'},
                      'sound': {'id': 'spell_engine:generic_healing_casting', 'randomness': 0.0}}},
          'release': {'animation': {'id': 'spell_engine:one_handed_area_release'},
                      'visuals': {'particles': [
                          particles('spell_engine:magic_holy', 60, color=HOLY, shape='PIPE', motion='FLOAT', lo=0.1,
                                    hi=0.2, vertical_origin=0.1, extent=8.0),
                          particles('spell_engine:area_effect_637', 1, color=GOLD, shape='NONE', anchor='GROUND',
                                    lo=0.0, hi=0.0)]},
                      'sound': {'id': 'spell_engine:generic_healing_release'}},
          'target': {'type': 'AREA', 'area': {'vertical_range_multiplier': 0.6, 'include_caster': True}},
          'impacts': [dict(effect('minecraft:absorption', 6, 1), visuals={'particles': holy}),
                      effect('minecraft:resistance', 6)],
          'cost': {'exhaust': 0.3, 'cooldown': {'duration': 30.0}, 'item': {'id': 'runes:healing_stone'}}}),
        ('wide_oath', 'upgrade', 'Wide Oath', 'Oathbound Aegis reaches {range_add} blocks further.',
         modifier(sch, oath, range_add=4.0)),
        ('mending_oath', 'upgrade', 'Mending Oath', 'Oathbound Aegis also heals everyone it shields for {heal}.',
         modifier(sch, oath, **append_impacts(heal(0.5)))),
        ('answering_light', 'capstone', 'Answering Light',
         'When you are hit, {trigger_chance} chance to smite the attacker with holy light for {damage} damage.',
         passive(sch, [chance('DAMAGE_TAKEN', 0.2)], [damage(0.6, 0.4, 'spell_engine:generic_healing_impact_1', holy)],
                 cooldown=3.0)),
        ('mending_strikes', 'passive', 'Mending Strikes', 'Melee hits have {trigger_chance} chance to heal you for '
         '{heal}.',
         passive(sch, [chance('MELEE_IMPACT', 0.15, target_override='CASTER')], [heal(0.3)], cooldown=2.0)),
        ('steadfast', 'passive', 'Steadfast', 'Blocking with a shield makes you take less damage for '
         '{effect_duration} sec.',
         passive(sch, [chance('SHIELD_BLOCK', 1)], [effect('minecraft:resistance', 3, 0, caster=True)], cooldown=1.0)),
        ('bulwark', 'stat', 'Bulwark', None, ('minecraft:generic.armor', 'addition', 2.0), 'minecraft:iron_chestplate'),
        ('consecrated_hands', 'stat', 'Blessed Hands', None, ('spell_power:healing', 'multiply_base', 0.03),
         'paladins:holy_wand'),
    ]


MASTERY = {'rogue': rogue, 'frost': frost, 'priest': priest, 'deadeye': deadeye, 'paladin': paladin}


# --------------------------------------------------------------------------------------
# Icons: original 16x16 pixel art, made here (no art copied from other mods).
# --------------------------------------------------------------------------------------
def png(path, pixels):
    raw = b''.join(b'\x00' + bytes(c for px in row for c in px) for row in pixels)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


GLYPHS = {
    'spell': lambda x, y: abs(x) + abs(y) <= 5,                       # diamond
    'upgrade': lambda x, y: (abs(x) <= 1 and -5 <= y <= 4) or (y == -5 + abs(x) and abs(x) <= 4),  # up arrow
    'capstone': lambda x, y: (x * x + y * y <= 25) and not (x * x + y * y <= 6),  # ring
    'passive': lambda x, y: x * x + y * y <= 12,                       # dot
}


def icon(path, kind, color, seed):
    r, g, b = color
    rows = []
    for py in range(16):
        row = []
        for px in range(16):
            x, y = px - 7.5, py - 7.5
            d = math.hypot(x, y)
            if d > 7.5:
                row.append((0, 0, 0, 0))
                continue
            if d > 6.6:  # frame
                row.append((40, 32, 24, 255))
                continue
            shade = 0.35 + 0.25 * ((px * 7 + py * 3 + seed) % 5) / 4
            px_col = (int(r * shade), int(g * shade), int(b * shade), 255)
            if GLYPHS[kind](round(x), round(y)):
                px_col = (min(255, r + 40), min(255, g + 40), min(255, b + 40), 255)
            row.append(px_col)
        rows.append(row)
    png(path, rows)


# --------------------------------------------------------------------------------------
# Trees
# --------------------------------------------------------------------------------------
def read_tree(server):
    for jar in glob.glob(os.path.join(server, 'mods', 'mrpgc_skill_tree-*.jar')):
        with zipfile.ZipFile(jar) as z:
            return {n: json.loads(z.read(TREE_PATH + n + '.json')) for n in ('skills', 'definitions', 'connections')}
    raise SystemExit('More RPG Classes skill tree jar not found')


def spell_reward(spell_id):
    return {'type': 'skill_tree_rpgs:spell', 'data': {'containers': [{
        'access': 'NONE', 'access_param': '', 'extra_tier_binding': 0, 'max_spell_count': 0, 'pool': '', 'slot': '',
        'spell_ids': [spell_id]}]}}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    tree = read_tree(sys.argv[1])
    skills, defs, conns = tree['skills'], tree['definitions'], tree['connections']
    os.makedirs(SPELLS, exist_ok=True)
    os.makedirs(ICONS, exist_ok=True)
    os.makedirs(TREES, exist_ok=True)
    for old in glob.glob(os.path.join(SPELLS, 'mastery_*.json')) + glob.glob(os.path.join(ICONS, 'mastery_*.png')):
        os.remove(old)
    lang = json.load(open(LANG, encoding='utf-8')) if os.path.exists(LANG) else {}
    lang = {k: v for k, v in lang.items() if '.mastery_' not in k}

    for cls, build in MASTERY.items():
        mod, school, color, items = build()
        nodes = {i: v for i, v in skills.items() if v['definition'].startswith(cls + '_')}
        root = next(v for v in nodes.values() if v.get('root'))
        t4 = {v['definition']: (i, v) for i, v in nodes.items() if 'tier_4' in v['definition']}
        cx = sum(v['x'] for _, v in t4.values()) / len(t4)
        cy = sum(v['y'] for _, v in t4.values()) / len(t4)
        dx, dy = cx - root['x'], cy - root['y']
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        px, py = -dy, dx  # perpendicular

        def at(out, side):
            return {'x': cx + dx * out + px * side, 'y': cy + dy * out + py * side}

        layout = {'spell': (70, 0), 'upgrade': [(110, -38), (110, 38)], 'capstone': (150, 0),
                  'passive': [(75, -80), (75, 80)], 'stat': [(115, -110), (115, 110)]}
        seen = {'upgrade': 0, 'passive': 0, 'stat': 0}
        ids = {}
        for seed, (key, kind, title, desc, data, *rest) in enumerate(items):
            def_id = f'mastery_{cls}_{key}'
            spell_id = f'minerpg:{def_id}'
            pos = layout[kind]
            if isinstance(pos, list):
                pos = pos[seen[kind]]
                seen[kind] += 1
            node_id = f'minerpg_{cls}_{key}'
            ids[kind if kind in ('spell', 'capstone') else f'{kind}{seen[kind]}'] = node_id
            skills[node_id] = dict(definition=def_id, **at(*pos))
            definition = {'description': {'skill_definition_id': def_id}, 'required_mods': [mod],
                          'title': {'translate': f'skill.minerpg.{def_id}.title'}}
            lang[f'skill.minerpg.{def_id}.title'] = title
            if kind == 'stat':
                attribute, op, value = data
                definition['icon'] = {'type': 'item', 'data': {'item': rest[0]}}
                definition['rewards'] = [{'type': 'puffish_skills:attribute',
                                          'data': {'attribute': attribute, 'operation': op, 'value': value}}]
            else:
                definition['icon'] = {'type': 'texture', 'data': {'texture': f'minerpg:textures/spell/{def_id}.png'}}
                definition['rewards'] = [spell_reward(spell_id)]
                with open(os.path.join(SPELLS, def_id + '.json'), 'w') as f:
                    json.dump(data, f, indent=2)
                    f.write('\n')
                lang[f'spell.minerpg.{def_id}.name'] = title
                lang[f'spell.minerpg.{def_id}.description'] = desc
                icon(os.path.join(ICONS, def_id + '.png'), kind, color, seed)
            defs[def_id] = definition

        # Connections: either tier-4 spell -> new spell -> upgrades and passives; upgrades -> capstone;
        # passives -> stats.
        pairs = []
        for name, (node_id, _) in t4.items():
            if name.endswith('_root') and 'spell' in name:
                pairs.append([node_id, ids['spell']])
        pairs += [[ids['spell'], ids['upgrade1']], [ids['spell'], ids['upgrade2']],
                  [ids['spell'], ids['passive1']], [ids['spell'], ids['passive2']],
                  [ids['upgrade1'], ids['capstone']], [ids['upgrade2'], ids['capstone']],
                  [ids['passive1'], ids['stat1']], [ids['passive2'], ids['stat2']]]
        conns['normal']['bidirectional'].extend(pairs)

    for name, obj in (('skills', skills), ('definitions', defs), ('connections', conns)):
        with open(os.path.join(TREES, name + '.json'), 'w') as f:
            json.dump(obj, f, separators=(',', ':'))
    os.makedirs(os.path.dirname(LANG), exist_ok=True)
    with open(LANG, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(lang.items())), f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'{len(MASTERY)} classes, {len(glob.glob(os.path.join(SPELLS, "mastery_*.json")))} spells -> {SPELLS}')


if __name__ == '__main__':
    main()
