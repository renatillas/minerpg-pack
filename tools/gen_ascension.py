#!/usr/bin/env python3
"""The Ascension talent tab (pack 1.8.0): pack/kubejs/data/minerpg/puffish_skills/categories/ascension/.

  python3 pack/tools/gen_ascension.py <mods dir> [--wip]      (dist/server/mods, or the scratch server's)

Design: docs/superpowers/specs/2026-11-11-minerpg-ascension-design.md. A third minerpg Pufferfish category with one
branch per Fate, filled only by boss points (quest rewards, source minerpg:bosses; no XP). Each Fate branch:
fate (root) -> 2 transformations (exclusive) -> 3 deepenings -> ultimate -> 2 empowerments.

Every skill gives the player the tag asc_<fate>_<node> (Pufferfish's tag reward; removed when the skill is locked or
reset), which the KubeJS side reads:
  kubejs/startup_scripts/minerpg_ascension.js   Fate = main class, 2 Deepenings, Orb reset, Spell Engine cast/heal hooks
  kubejs/server_scripts/minerpg_ascension.js    the tab gate, migration, and the effects data can't express
  kubejs/server_scripts/minerpg_ascension_effects.js
What data can express is data: attributes, passive spells (triggers), modifiers of the class spells, active Ultimates.
Harmful impacts carry NOT_PLAYER so nothing here can hurt a party member.

Writes: the category, kubejs/data/minerpg/spell/ascension_*.json, icons, lang keys, kubejs/ascension/rules.json.
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spell_lib as sl  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'puffish_skills', 'categories', 'ascension')
SIDE = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'puffish_skills', 'categories', 'side_skills')
SPELLS = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'spell')
ICONS = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'textures', 'spell')
LANG = os.path.join(ROOT, 'kubejs', 'assets', 'minerpg', 'lang', 'en_us.json')
RULES = os.path.join(ROOT, 'kubejs', 'ascension', 'rules.json')

WAVE = ['rogue', 'warrior', 'priest', 'paladin']
FATE_CLASSES = {'nightblade': 'rogue', 'plaguefang': 'rogue', 'juggernaut': 'warrior', 'reaver': 'warrior',
                'lightbinder': 'priest', 'zealot': 'priest', 'bulwark': 'paladin', 'crusader': 'paladin'}
NODES = ['fate', 'trans_1', 'trans_2', 'deep_1', 'deep_2', 'deep_3', 'ultimate', 'emp_dragon', 'emp_wither']
POINTS = 7
MAX_DEEPENINGS = 2
# Icon glyph per node (spell_lib.GLYPHS) and the branch layout: one column per Fate, one row per boss.
GLYPH = {'fate': 'capstone', 'trans': 'spell', 'deep': 'passive', 'ultimate': 'spell', 'emp': 'upgrade'}
COLUMN = 130
ROW = 70
OFFSETS = {'fate': (0, 0), 'trans_1': (-28, 1), 'trans_2': (28, 1), 'deep_1': (-40, 2), 'deep_2': (0, 2),
           'deep_3': (40, 2), 'ultimate': (0, 3), 'emp_dragon': (-28, 4), 'emp_wither': (28, 4)}

# Every harmful impact gets this: skip players, so nothing in Ascension can hit a party member.
NOT_PLAYER = {'conditions': [{'entity_type': 'minecraft:player'}], 'execute': 'DENY'}

# Fate stat changes that KubeJS has to correct for: holy damage and healing are one stat (spell_power:healing), so a
# healing change also moves holy damage. These multiply spell_power:healing damage dealt by the Fate's holder so it
# ends where the design says (written to rules.json; minerpg_ascension_effects.js applies them).
HOLY_DAMAGE_TARGET = {'lightbinder': 0.5, 'zealot': 1.0, 'crusader': 1.0}


def skill_id(fate, node):
    return f'asc_{fate}_{node}'


def spell_id(fate, node, part=None):
    return f'minerpg:ascension_{fate}_{node}' + (f'_{part}' if part else '')


def harmful(impact):
    """Mark a harmful impact player-proof."""
    impact = dict(impact)
    impact['target_modifiers'] = list(impact.get('target_modifiers', [])) + [NOT_PLAYER]
    return impact


# --------------------------------------------------------------------------------------
# The Fates. Each returns {node: dict(title, text, [drawback], attrs=[(attribute, operation, value)],
#                                     spells={part or '': spell json})}.
# Text is the tooltip; numbers are written out (the design's first guesses, tuned in playtest).
# --------------------------------------------------------------------------------------
FATES = {}

MELEE = 'spell_power:physical_melee'
HOLY = 'spell_power:healing'
GOLD, WHITE = 4294954111, 4294967295


def fate(fn):
    FATES[fn.__name__] = fn
    return fn


def active(school, impacts, cooldown, target=None, range_=0.0, release_anim='spell_engine:one_handed_area_release',
           parts=(), sound=None, cast=None):
    """An active spell (Ultimates). With no target, it is cast on yourself."""
    s = {'school': school, 'range': range_, 'tier': 5, 'learn': {}, 'active': {'cast': cast or {}},
         'release': {'animation': {'id': release_anim}},
         'target': target or {'type': 'CASTER'}, 'impacts': impacts,
         'cost': {'exhaust': 0.3, 'cooldown': {'duration': cooldown}}}
    if parts:
        s['release']['visuals'] = {'particles': list(parts)}
    if sound:
        s['release']['sound'] = {'id': sound}
    return s


def area(radius):
    return {'type': 'AREA', 'area': {'vertical_range_multiplier': 0.6}}


def stacking(effect_id, duration, cap, stacks=1):
    """A status effect that adds stacks per hit (amplifier 0..cap)."""
    e = sl.effect(effect_id, duration, stacks - 1)
    e['action']['status_effect'].update({'apply_mode': 'ADD', 'amplifier_cap': cap})
    return e


def below(fraction):
    return {'health_percent_below': fraction}


def caster_below(trigger, fraction):
    trigger['caster_conditions'] = [below(fraction)]
    return trigger


def ring(pid, count, color=None, extent=6.0):
    return sl.particles(pid, count, color=color, shape='PIPE', motion='FLOAT', lo=0.1, hi=0.3, vertical_origin=0.1,
                        extent=extent)


VENOM = 'mrpg_lib:fatal_poison'  # a poison that can kill (vanilla Poison stops at 1 health)


@fate
def nightblade():
    smoke = [sl.particles('spell_engine:smoke_medium', 40, shape='SPHERE', lo=0.15, hi=0.3)]
    cuts = [ring('spell_engine:sweep', 40, extent=6.0), sl.particles('spell_engine:smoke_medium', 40, lo=0.2, hi=0.4)]
    ult = 'minerpg:ascension_nightblade_ultimate'
    return {
        'fate': dict(title='Nightblade', text='Ambush: your first melee hit after Vanish or Shadow Step deals +150% '
                     'damage.', drawback='-20% max health.',
                     attrs=[('minecraft:generic.max_health', 'multiply_base', -0.2)]),
        'trans_1': dict(title='Severing Step', text='Shadow Step\'s cooldown resets if its target dies within 3 seconds.',
                        spells={'': sl.modifier(MELEE, 'rogues:shadow_step', effect_duration_add=1.5)}),
        'trans_2': dict(title='Smoke Exit', text='Leaving Vanish blinds and slows enemies within 4 blocks for 2 '
                        'seconds.'),
        'deep_1': dict(title='Killing Rhythm', text='A kill gives +25% movement speed and attack speed for 4 seconds.'),
        'deep_2': dict(title='Exposed Throat', text='Ambush hits crack the target\'s armor (Shatter) for 5 seconds.'),
        'deep_3': dict(title='Fade', text='Dropping below 30% health hides you in Vanish. Once per minute.',
                       spells={'': sl.passive(MELEE, [caster_below(sl.chance('DAMAGE_TAKEN', 1, target_override='CASTER'),
                                                                   0.3)],
                                              [dict(sl.effect('rogues:stealth', 6, 0, caster=True),
                                                    visuals={'particles': smoke})], cooldown=60.0)}),
        'ultimate': dict(title='Thousand Cuts', text='Ultimate (Ender Guardian): a storm of blades hits every enemy '
                         'within 6 blocks for heavy weapon damage. Every hit is critical. 60 s cooldown.',
                         spells={'': active(MELEE, [harmful(dict(sl.damage(2.4, 0.4), target_modifiers=[
                             {'conditions': [], 'execute': 'PASS', 'modifier': {'critical_chance_bonus': 1.0}}]))],
                             60.0, target=area(6.0), range_=6.0, release_anim='spell_engine:dual_handed_weapon_cross',
                             parts=cuts, sound='rogues:mortal_strike_impact')}),
        'emp_dragon': dict(title='Bloodied Blades', text='Thousand Cuts also makes its targets bleed.',
                           spells={'': sl.modifier(MELEE, ult, **sl.append_impacts(
                               harmful(sl.effect('spell_engine:bleed', 6, 1))))}),
        'emp_wither': dict(title='Endless Cuts', text='Each kill by Thousand Cuts takes 10 seconds off its '
                           'cooldown.'),
    }


@fate
def plaguefang():
    venom = harmful(stacking(VENOM, 6, 4))
    gas = [sl.particles('spell_engine:smoke_medium', 30, color=4284940287, lo=0.1, hi=0.25)]
    return {
        'fate': dict(title='Plaguefang', text='Venom: every melee hit adds a stack of Fatal Poison (up to 5).',
                     drawback='-20% melee damage.', attrs=[('minecraft:generic.attack_damage', 'multiply_base', -0.2)],
                     spells={'': sl.passive(MELEE, [sl.chance('MELEE_IMPACT', 1, cap_per_tick=1)], [venom])}),
        'trans_1': dict(title='Rupture', text='Mutilate tears the Venom out of its target in one burst of damage.',
                        spells={'': sl.modifier(MELEE, 'rogues:mutilate', **sl.append_impacts(
                            harmful(sl.damage(1.2, 0.2, parts=gas))))}),
        'trans_2': dict(title='Toxic Snare', text='Bear Trap adds 3 Venom stacks and spreads them to enemies within 4 '
                        'blocks.',
                        spells={'': sl.modifier(MELEE, 'rogues:bear_trap', replacing_area_impact=sl.area_impact(4.0, gas),
                                                **sl.append_impacts(harmful(stacking(VENOM, 8, 4, stacks=3))))}),
        'deep_1': dict(title='Virulence', text='When a poisoned enemy dies, its Venom jumps to the nearest enemy.'),
        'deep_2': dict(title='Numbing Agent', text='Enemies with 3 or more Venom stacks are slowed by 30%.'),
        'deep_3': dict(title='Inured', text='You are immune to poison.'),
        'ultimate': dict(title='Plague Bloom', text='Ultimate (Ender Guardian): for 8 seconds a toxic cloud follows '
                         'you. Enemies within 5 blocks gain a Venom stack every second and deal less damage. '
                         '60 s cooldown.',
                         spells={'': active(MELEE, [dict(sl.effect('minecraft:resistance', 0.5, 0, caster=True))], 60.0,
                                            release_anim='spell_engine:dual_handed_ground_release',
                                            parts=[ring('spell_engine:smoke_medium', 80, 4284940287, 5.0)])}),
        'emp_dragon': dict(title='Spreading Bloom', text='Plague Bloom reaches 50% further, and you heal for each '
                           'enemy inside it.'),
        'emp_wither': dict(title='Corpse Burst', text='Enemies that die inside Plague Bloom burst, giving nearby '
                           'enemies full Venom.'),
    }


def self_effect(effect_id, seconds, amplifier=0):
    return sl.effect(effect_id, seconds, amplifier, caster=True)


@fate
def juggernaut():
    quake = [ring('spell_engine:smoke_medium', 60, extent=4.0)]
    return {
        'fate': dict(title='Juggernaut', text='Unstoppable: +30% max health and +4 armor. Charge knocks enemies aside '
                     'and makes them attack you.', drawback='-15% movement speed and attack speed.',
                     attrs=[('minecraft:generic.max_health', 'multiply_base', 0.3),
                            ('minecraft:generic.armor', 'addition', 4.0),
                            ('minecraft:generic.movement_speed', 'multiply_base', -0.15),
                            ('minecraft:generic.attack_speed', 'multiply_base', -0.15)]),
        'trans_1': dict(title='Unbroken', text='While Last Stand lasts, enemies within 8 blocks attack you, and 30% of '
                        'the damage you take strikes back at the attacker.'),
        'trans_2': dict(title='Rallying Cry', text='Shout also gives you and every ally within 8 blocks a barrier that '
                        'absorbs 4 damage for 8 seconds.'),
        'deep_1': dict(title='Iron Hide', text='You take 10% less damage while above half health.'),
        'deep_2': dict(title='Shield Slam', text='Blocking with a shield knocks back the attacker and enemies near it.',
                       spells={'': dict(sl.passive(MELEE, [sl.chance('SHIELD_BLOCK', 1)], [
                           harmful({'action': {'type': 'VELOCITY', 'velocity': {
                               'frame': 'ORIGIN', 'push': {'x': 0.0, 'y': 0.3, 'z': 1.2}, 'intent': 'HARMFUL'}}})],
                           cooldown=1.0, area=sl.area_impact(3.0, quake)))}),
        'deep_3': dict(title='Second Wind', text='Dropping below 30% health gives you strong regeneration for 5 '
                       'seconds. Once per minute.',
                       spells={'': sl.passive(MELEE, [caster_below(sl.chance('DAMAGE_TAKEN', 1, target_override='CASTER'),
                                                                   0.3)],
                                              [self_effect('minecraft:regeneration', 5, 2)], cooldown=60.0)}),
        'ultimate': dict(title='Colossus', text='Ultimate (Ender Guardian): for 10 seconds you grow 30% larger, cannot '
                         'be knocked back, and take 50% less damage. 90 s cooldown.',
                         spells={'': active(MELEE, [self_effect('minecraft:resistance', 10, 1)], 90.0,
                                            release_anim='spell_engine:one_handed_shout_release',
                                            parts=quake, sound='rogues:shout_release')}),
        'emp_dragon': dict(title='Bulwark of Giants', text='While Colossus lasts, allies within 8 blocks take 20% less '
                           'damage.'),
        'emp_wither': dict(title='Earthshaker', text='Colossus ends with a ground slam that stuns enemies within 6 '
                           'blocks for 2 seconds.'),
    }


@fate
def reaver():
    blood = [sl.particles('spell_engine:dripping_blood', 30, lo=0.2, hi=0.4)]
    execute = harmful(dict(sl.damage(1.5, 0.3, parts=blood), target_modifiers=[
        {'conditions': [below(0.35)], 'execute': 'ALLOW'}]))
    headsman = harmful(dict(sl.damage(100.0, 0.5, parts=blood), target_modifiers=[
        {'conditions': [below(0.15)], 'execute': 'ALLOW'},
        {'conditions': [{'entity_type': '#minerpg:boss'}], 'execute': 'DENY'}]))
    return {
        'fate': dict(title='Reaver', text='Finisher: Mortal Strike deals double damage to enemies below 35% health, '
                     'and kills reset Charge.', drawback='-30% healing received.',
                     attrs=[('spell_engine:healing_taken', 'multiply_base', -0.3)],
                     spells={'': sl.modifier(MELEE, 'rogues:mortal_strike', **sl.append_impacts(execute))}),
        'trans_1': dict(title='Headsman\'s Throw', text='Throw kills any enemy below 15% health outright (not bosses).',
                        spells={'': sl.modifier(MELEE, 'rogues:throw', **sl.append_impacts(headsman))}),
        'trans_2': dict(title='Bloodletting', text='Mortal Strike\'s bleed is stronger, and Mortal Strike heals you for '
                        '20% of its damage.',
                        spells={'': sl.modifier(MELEE, 'rogues:mortal_strike', effect_amplifier_add=1)}),
        'deep_1': dict(title='Momentum', text='Each kill gives +10% attack speed for 6 seconds, stacking 3 times.'),
        'deep_2': dict(title='Cleave', text='Mortal Strike also hits enemies next to its target for half its damage.'),
        'deep_3': dict(title='Scent of Blood', text='+15% melee damage against enemies below half health.'),
        'ultimate': dict(title='Rampage', text='Ultimate (Ender Guardian): for 8 seconds every kill resets your spell '
                         'cooldowns, and you move 30% faster. 90 s cooldown.',
                         spells={'': active(MELEE, [self_effect('minecraft:speed', 8, 1)], 90.0,
                                            release_anim='spell_engine:one_handed_shout_release',
                                            parts=blood, sound='rogues:shout_release')}),
        'emp_dragon': dict(title='Blood Frenzy', text='While Rampage lasts, you heal for 15% of the damage you deal.'),
        'emp_wither': dict(title='No End', text='Each kill during Rampage makes it last 1 second longer.'),
    }


HOLY_PARTS = [sl.particles('spell_engine:magic_holy', 30, color=4294954239, motion='DECELERATE', lo=0.2, hi=0.4)]


@fate
def lightbinder():
    return {
        'fate': dict(title='Lightbinder', text='Overflow: healing beyond full health becomes a barrier (up to 6 '
                     'hearts). +30% healing power.', drawback='-50% holy damage.',
                     attrs=[(HOLY, 'multiply_base', 0.3)]),
        'trans_1': dict(title='Living Barrier', text='Your Barrier heals allies standing near it every second.'),
        'trans_2': dict(title='Purifying Well', text='Each heal from your Lightwell also removes one harmful effect.'),
        'deep_1': dict(title='Guardian\'s Echo', text='When you heal an ally below 30% health, the heal lands twice.'),
        'deep_2': dict(title='Swift Grace', text='+15% spell haste.', attrs=[('spell_power:haste', 'multiply_base', 0.15)]),
        'deep_3': dict(title='Sanctuary', text='Allies within 6 blocks of you take 8% less damage.'),
        'ultimate': dict(title='Dawnfall', text='Ultimate (Ender Guardian): for 8 seconds every heal you cast also '
                         'lands on every ally within 12 blocks, and an ally who would die is held at 1 health '
                         'instead (once each). 120 s cooldown.',
                         spells={'': active(HOLY, [dict(sl.heal(0.5), visuals={'particles': HOLY_PARTS})], 120.0,
                                            cast={'duration': 0.5, 'animation': {'id': 'spell_engine:one_handed_area_charge'}},
                                            parts=[ring('spell_engine:magic_holy', 80, 4294954239, 12.0)],
                                            sound='spell_engine:generic_healing_release')}),
        'emp_dragon': dict(title='First Light', text='Dawnfall starts by cleansing every harmful effect from your '
                           'allies.'),
        'emp_wither': dict(title='Long Dawn', text='Dawnfall lasts 4 seconds longer, and allies heal 5% of their '
                           'health every second during it.'),
    }


@fate
def zealot():
    return {
        'fate': dict(title='Zealot', text='Righteous Fire: 40% of the holy damage you deal heals the most injured ally '
                     'near you (yourself included).', drawback='-30% healing power on your heals.',
                     attrs=[(HOLY, 'multiply_base', -0.3)]),
        'trans_1': dict(title='Chained Penance', text='Penance\'s bolts jump to a second enemy.',
                        spells={'': sl.modifier(HOLY, 'paladins:penance',
                                                projectile_perks={'ricochet': 1, 'ricochet_range': 8.0})}),
        'trans_2': dict(title='Hallowed Ground', text='Holy Beam leaves burning holy ground under its target for 4 '
                        'seconds.'),
        'deep_1': dict(title='Fervor', text='Each holy hit gives +3% spell haste for 5 seconds, stacking 5 times.'),
        'deep_2': dict(title='Martyrdom', text='When you are hit, enemies within 4 blocks take holy damage.',
                       spells={'': dict(sl.passive(HOLY, [sl.chance('DAMAGE_TAKEN', 1, target_override='CASTER')], [
                           harmful(dict(sl.damage(0.4, 0.2), action=dict(sl.damage(0.4, 0.2)['action'],
                                                                          allow_on_center_target=False)))],
                           cooldown=1.0, area=sl.area_impact(4.0, HOLY_PARTS)))}),
        'deep_3': dict(title='Smite the Wicked', text='+25% holy damage against undead.'),
        'ultimate': dict(title='Wrath of Dawn', text='Ultimate (Ender Guardian): over 3 seconds, 5 pillars of light '
                         'strike enemies around you; each one heals allies near it. 90 s cooldown.',
                         spells={'': active(HOLY, [dict(sl.effect('minecraft:glowing', 0.5, 0, caster=True))], 90.0,
                                            cast={'duration': 0.5, 'animation': {'id': 'spell_engine:one_handed_area_charge'}},
                                            parts=[ring('spell_engine:magic_holy', 80, 4294954111, 10.0)],
                                            sound='spell_engine:generic_healing_release')}),
        'emp_dragon': dict(title='Blinding Light', text='Wrath of Dawn\'s pillars stun for 1 second.'),
        'emp_wither': dict(title='Final Dawn', text='Wrath of Dawn calls 9 pillars.'),
    }


@fate
def bulwark():
    block_heal = sl.passive(HOLY, [sl.chance('SHIELD_BLOCK', 1, target_override='CASTER')],
                            [dict(sl.heal(0.4), visuals={'particles': HOLY_PARTS})], cooldown=1.0)
    taunt = sl.passive(HOLY, [sl.chance('SHIELD_BLOCK', 1, target_override='CASTER')],
                       [harmful({'action': {'type': 'AGGRO', 'aggro': {'mode': 'SET', 'only_if_targeted': False},
                                            'allow_on_center_target': False}})],
                       cooldown=1.0, area=sl.area_impact(6.0, HOLY_PARTS))
    return {
        'fate': dict(title='Bulwark', text='Hold the Line: +20% max health. Blocking with a shield heals you and makes '
                     'enemies within 6 blocks attack you.', drawback='-25% attack damage.',
                     attrs=[('minecraft:generic.max_health', 'multiply_base', 0.2),
                            ('minecraft:generic.attack_damage', 'multiply_base', -0.25)],
                     spells={'heal': block_heal, 'taunt': taunt},
                     spell_names={'heal': 'Hold the Line', 'taunt': 'Hold the Line: Taunt'}),
        'trans_1': dict(title='Shared Protection', text='Divine Protection also protects allies within 6 blocks.'),
        'trans_2': dict(title='Banner of Resolve', text='Allies standing in your Battle Banner also take less damage.',
                        spells={'': sl.modifier(HOLY, 'paladins:battle_banner', **sl.append_impacts(
                            sl.effect('minecraft:resistance', 2, 0)))}),
        'deep_1': dict(title='Steadfast', text='Blocking with a shield makes you take less damage for 3 seconds.',
                       spells={'': sl.passive(HOLY, [sl.chance('SHIELD_BLOCK', 1)],
                                              [self_effect('minecraft:resistance', 3, 0)], cooldown=1.0)}),
        'deep_2': dict(title='Holy Retort', text='When hit in melee, you smite the attacker with holy light. At most '
                       'once every 2 seconds.',
                       spells={'': sl.passive(HOLY, [sl.chance('DAMAGE_TAKEN', 1)],
                                              [harmful(sl.damage(0.6, 0.4, parts=HOLY_PARTS))], cooldown=2.0)}),
        'deep_3': dict(title='Unyielding', text='You cannot be knocked back.',
                       attrs=[('minecraft:generic.knockback_resistance', 'addition', 1.0)]),
        'ultimate': dict(title='Bastion of Light', text='Ultimate (Ender Guardian): plant a dome 8 blocks wide for 8 '
                         'seconds. Allies inside take 60% less damage and enemies inside are slowed. You cannot move '
                         'while it stands. 120 s cooldown.',
                         spells={'': active(HOLY, [self_effect('minecraft:slowness', 8, 6)], 120.0,
                                            parts=[ring('spell_engine:magic_holy', 100, 4294954111, 4.0)],
                                            sound='spell_engine:generic_healing_release')}),
        'emp_dragon': dict(title='Sacred Ground', text='Bastion of Light heals allies inside 1 heart every second.'),
        'emp_wither': dict(title='Searing Dome', text='Enemies inside Bastion of Light burn with holy fire.'),
    }


@fate
def crusader():
    return {
        'fate': dict(title='Crusader', text='Blessed Arms: your melee hits deal extra holy damage equal to 30% of your '
                     'healing power.', drawback='-4 armor and -20% healing power.',
                     attrs=[('minecraft:generic.armor', 'addition', -4.0), (HOLY, 'multiply_base', -0.2)]),
        'trans_1': dict(title='Avenger\'s Leap', text='Judgement leaps you to its target.'),
        'trans_2': dict(title='Searing Judgement', text='Judgement stuns 2 seconds longer and sets its target ablaze.',
                        spells={'': sl.modifier(MELEE, 'paladins:judgement', effect_duration_add=2.0,
                                                **sl.append_impacts(harmful({'action': {
                                                    'type': 'FIRE', 'fire': {'duration': 4.0}}})))}),
        'deep_1': dict(title='Zeal', text='A kill gives +20% attack speed for 3 seconds.'),
        'deep_2': dict(title='Consuming Light', text='Immolation reaches 50% further.',
                       spells={'': sl.modifier(HOLY, 'paladins:immolation', range_add=2.5)}),
        'deep_3': dict(title='Light\'s Reprisal', text='Your melee hits heal you for 3% of the damage dealt.'),
        'ultimate': dict(title='Avatar of Light', text='Ultimate (Ender Guardian): for 10 seconds, wings of light: '
                         '+30% attack damage, immunity to fire, and every melee hit sends out a holy shockwave. '
                         '90 s cooldown.',
                         spells={'': active(HOLY, [self_effect('minecraft:fire_resistance', 10, 0)], 90.0,
                                            parts=HOLY_PARTS + [ring('spell_engine:magic_holy', 60, 4294954111, 3.0)],
                                            sound='spell_engine:generic_healing_release')}),
        'emp_dragon': dict(title='Heaven\'s Wings', text='While Avatar of Light lasts you fall slowly and jump higher.'),
        'emp_wither': dict(title='Shared Radiance', text='While Avatar of Light lasts, allies within 8 blocks heal 2% '
                           'of the damage you deal.'),
    }


# --------------------------------------------------------------------------------------
def check(defs, skills, connections, rules, spells, wip=False):
    errors = []
    roots = [s for s, v in skills.items() if v.get('root')]
    if len(roots) != len(FATE_CLASSES) and not wip:
        errors.append(f'{len(roots)} roots, expected {len(FATE_CLASSES)}')
    for fate in FATE_CLASSES:
        if fate not in FATES:
            if not wip:
                errors.append(f'{fate}: not designed yet')
            continue
        for node in NODES:
            sid = skill_id(fate, node)
            if sid not in skills or sid not in defs:
                errors.append(f'{sid}: missing')
        fate_def = defs.get(skill_id(fate, 'fate'), {})
        if 'Drawback' not in json.dumps(fate_def.get('description', {})) and \
                'drawback' not in json.dumps(fate_def.get('description', {})):
            errors.append(f'{fate}: the Fate tooltip has no drawback line')
    for sid, d in defs.items():
        for reward in d.get('rewards', []):
            if reward['type'] == 'skill_tree_rpgs:spell':
                for container in reward['data']['containers']:
                    for spell in container['spell_ids']:
                        if spell.startswith('minerpg:') and spell not in spells:
                            errors.append(f'{sid}: grants {spell}, which is not written')
    for sid, s in spells.items():
        for m in s.get('modifiers', []):
            pattern = m['spell_pattern']
            if pattern.startswith('minerpg:') and pattern not in spells:
                errors.append(f'{sid}: modifies {pattern}, which does not exist')
        for impact in all_impacts(s):
            action = impact['action']
            if action['type'] in ('DAMAGE', 'FIRE', 'AGGRO', 'VELOCITY', 'TELEPORT') or (
                    action['type'] == 'STATUS_EFFECT' and not action.get('apply_to_caster') and
                    action['status_effect']['effect_id'] in HARMFUL_EFFECTS):
                if action.get('apply_to_caster'):
                    continue
                if NOT_PLAYER not in impact.get('target_modifiers', []):
                    errors.append(f'{sid}: a harmful {action["type"]} impact can hit players')
    exclusive = connections['exclusive']['bidirectional']
    for fate in FATES:
        if [skill_id(fate, 'trans_1'), skill_id(fate, 'trans_2')] not in exclusive:
            errors.append(f'{fate}: the two transformations are not exclusive')
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)


HARMFUL_EFFECTS = {'minecraft:poison', 'minecraft:slowness', 'minecraft:weakness', 'minecraft:blindness',
                   'spell_engine:bleed', 'rogues:shatter', 'rogues:shock', 'minecraft:wither', VENOM}


def all_impacts(spell):
    out = list(spell.get('impacts', []))
    for m in spell.get('modifiers', []):
        out += m.get('impacts', [])
    return out


# --------------------------------------------------------------------------------------
def build():
    defs, skills, spells, lang = {}, {}, {}, {}
    normal, exclusive = [], []
    rules = {'wave': WAVE, 'fate_roots': {}, 'deepenings': {}, 'max_deepenings': MAX_DEEPENINGS,
             'holy_damage_multiplier': {}}
    for col, fate in enumerate(FATE_CLASSES):
        if fate not in FATES:
            continue
        cls = FATE_CLASSES[fate]
        design = FATES[fate]()
        color = CLASS_COLOR[cls]
        for seed, node in enumerate(NODES):
            n = design[node]
            sid = skill_id(fate, node)
            dx, row = OFFSETS[node]
            skills[sid] = {'definition': sid, 'x': (col - (len(FATE_CLASSES) - 1) / 2) * COLUMN + dx, 'y': row * ROW}
            rewards = [{'type': 'puffish_skills:tag', 'data': {'tag': sid}}]
            rewards += [{'type': 'puffish_skills:attribute', 'data': {'attribute': a, 'operation': op, 'value': v}}
                        for a, op, v in n.get('attrs', [])]
            granted = []
            for part, spell in n.get('spells', {}).items():
                spid = spell_id(fate, node, part or None)
                spells[spid] = spell
                lang[f'spell.{spid.replace(":", ".")}.name'] = n.get('spell_names', {}).get(part, n['title'])
                lang[f'spell.{spid.replace(":", ".")}.description'] = n.get('spell_texts', {}).get(part, n['text'])
                granted.append(spid)
            if granted:
                rewards.append(sl.spell_reward(granted[0]))
                rewards[-1]['data']['containers'][0]['spell_ids'] = granted
            lang[f'skill.minerpg.{sid}.title'] = n['title']
            lang[f'skill.minerpg.{sid}.description'] = n['text']
            description = {'translate': f'skill.minerpg.{sid}.description'}
            if 'drawback' in n:
                lang[f'skill.minerpg.{sid}.drawback'] = 'Drawback: ' + n['drawback']
                description = {'text': '', 'extra': [description, {'text': '\n'},
                                                     {'translate': f'skill.minerpg.{sid}.drawback', 'color': 'gold'}]}
            kind = node.split('_')[0]
            icon_path = f'minerpg:textures/spell/ascension_{fate}_{node}.png'
            defs[sid] = {'title': {'translate': f'skill.minerpg.{sid}.title'}, 'description': description,
                         'icon': {'type': 'texture', 'data': {'texture': icon_path}}, 'rewards': rewards,
                         '_icon': (GLYPH[kind], color, seed)}
        skills[skill_id(fate, 'fate')]['root'] = True
        f = lambda node: skill_id(fate, node)  # noqa: E731
        normal += [[f('fate'), f('trans_1')], [f('fate'), f('trans_2')]]
        normal += [[f(t), f(d)] for t in ('trans_1', 'trans_2') for d in ('deep_1', 'deep_2', 'deep_3')]
        normal += [[f(d), f('ultimate')] for d in ('deep_1', 'deep_2', 'deep_3')]
        normal += [[f('ultimate'), f('emp_dragon')], [f('ultimate'), f('emp_wither')]]
        exclusive.append([f('trans_1'), f('trans_2')])
        rules['fate_roots'][f('fate')] = cls
        rules['deepenings'][fate] = [f('deep_1'), f('deep_2'), f('deep_3')]
        if fate in HOLY_DAMAGE_TARGET:
            healing = sum(v for a, op, v in design['fate'].get('attrs', [])
                          if a == 'spell_power:healing' and op == 'multiply_base')
            rules['holy_damage_multiplier'][f('fate')] = round(HOLY_DAMAGE_TARGET[fate] / (1 + healing), 4)
    connections = {'normal': {'bidirectional': normal}, 'exclusive': {'bidirectional': exclusive}}
    return defs, skills, connections, rules, spells, lang


CLASS_COLOR = {'rogue': (120, 110, 160), 'warrior': (190, 80, 60), 'priest': (240, 235, 200), 'paladin': (255, 200, 80)}


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        json.dump(obj, fh, indent=1)
        fh.write('\n')


def main():
    args = [a for a in sys.argv[1:] if a != '--wip']
    if len(args) != 1:
        raise SystemExit(__doc__)
    defs, skills, connections, rules, spells, lang = build()
    # --wip: write the Fates designed so far (testing a class before the others exist).
    check(defs, skills, connections, rules, spells, wip='--wip' in sys.argv)
    for old in glob.glob(os.path.join(SPELLS, 'ascension_*.json')) + glob.glob(os.path.join(ICONS, 'ascension_*.png')):
        os.remove(old)
    os.makedirs(ICONS, exist_ok=True)
    for sid, d in defs.items():
        glyph, color, seed = d.pop('_icon')
        sl.icon(os.path.join(ICONS, f'ascension_{sid[len("asc_"):]}.png'), glyph, color, seed)
    for spid, spell in spells.items():
        write(os.path.join(SPELLS, spid.split(':')[1] + '.json'), spell)
    with open(os.path.join(SIDE, 'category.json')) as fh:
        category = json.load(fh)
    category.update({'title': 'Ascension', 'unlocked_by_default': False, 'spent_points_limit': POINTS,
                     'exclusive_root': True})
    write(os.path.join(OUT, 'category.json'), category)
    write(os.path.join(OUT, 'definitions.json'), defs)
    write(os.path.join(OUT, 'skills.json'), skills)
    write(os.path.join(OUT, 'connections.json'), connections)
    write(RULES, rules)
    current = json.load(open(LANG, encoding='utf-8'))
    current = {k: v for k, v in current.items() if '.ascension_' not in k and '.asc_' not in k}
    current.update(lang)
    with open(LANG, 'w', encoding='utf-8') as fh:
        json.dump(dict(sorted(current.items())), fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    print(f'{len(FATES)} fates, {len(skills)} skills, {len(spells)} spells -> {OUT}')


if __name__ == '__main__':
    main()
