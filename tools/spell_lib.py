"""Shared building blocks for the pack's generated Spell Engine spells and Skill Tree skills.

Used by gen_ascension.py (and gen_trophy_icons.py for png). Spell json follows Spell Engine 1.10 (docs:
github.com/ZsoltMolnarrr/SpellEngine/tree/main/docs). Icons are original 16x16 pixel art made here.
"""
import math
import struct
import zlib


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

# Attribute skills' tooltip text. Skill Tree RPGs only fills tooltips for its own skills (a client-side list keyed by
# skill id), so attribute skills carry their text as a plain translation; spell skills get their tooltip from a
# client script that adds them to that list (kubejs/client_scripts/minerpg_ascension_tooltips.js).
ATTR_TEXT = {
    'minecraft:generic.armor': '+{v:g} armor',
    'minecraft:generic.attack_damage': '+{p:g}% melee damage',
    'minecraft:generic.attack_speed': '+{p:g}% attack speed',
    'minecraft:generic.max_health': '+{v:g} max health',
    'ranged_weapon:damage': '+{p:g}% ranged damage',
    'spell_power:frost': '+{p:g}% frost spell power',
    'spell_power:haste': '+{p:g}% spell haste',
    'spell_power:healing': '+{p:g}% healing power',
}

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


def spell_reward(spell_id):
    return {'type': 'skill_tree_rpgs:spell', 'data': {'containers': [{
        'access': 'NONE', 'access_param': '', 'extra_tier_binding': 0, 'max_spell_count': 0, 'pool': '', 'slot': '',
        'spell_ids': [spell_id]}]}}
