#!/usr/bin/env python3
"""The eight origins (races) and their powers: config/originpacks/minerpg_races/data/minerpg/origins/.

  python3 pack/tools/gen_origins.py

Pack 1.6.0 redesign (designer, 2026-11-05), docs/superpowers/specs/2026-11-05-minerpg-origins-redesign.md:
every origin has one signature strength (about +15-25% in its speciality), one or two active abilities that do
something other than a potion effect, one real drawback, and its own size.

Party safety: PvP is on (server.properties), so nothing hostile here touches players. Every area ability filters
its targets to non-players (NOT_PLAYER; tested: area conditions run on players, creatures pass), pushes use
include_players false, and the on-hit perks skip player victims (in the script).
NeoOrigins' own ground_slam, tidal_wave, active_dash damage and active_fireball have no target filter, so they are
not used; the same abilities are built from active_ability + area_of_effect instead.

Vein Miner, Searing and Chilling Strikes, Feign Death's aggro drop and the one free Orb of Origin are in
kubejs/server_scripts/minerpg_origins.js (those powers are neoorigins:simple markers here). NeoOrigins conditions
only evaluate on players, so an on-hit filter on the victim ("not a player") silently fails; the script does it.
Ability keys: active powers take the NeoOrigins skill keys in the order they are listed below (Skill 1, 2, 3).
"""

import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE = os.path.join(ROOT, 'config', 'originpacks', 'minerpg_races', 'data', 'minerpg', 'origins')
POWERS = os.path.join(BASE, 'powers')

NOT_PLAYER = {'type': 'neoorigins:not', 'condition': {'type': 'neoorigins:entity_type', 'entity_type': 'minecraft:player'}}
# The spell schools that have real spells in this pack (counted across every mod's spell files, 2026-11-05).
SPELL_SCHOOLS = ['arcane', 'fire', 'frost', 'healing', 'earth', 'water', 'air']
SECONDS = 20


def text(s):
    return {'text': s}


def attr(attribute, amount, operation='add_value', **extra):
    return {'type': 'neoorigins:attribute_modifier', 'attribute': attribute, 'amount': amount,
            'operation': operation, **extra}


def spell_bonus(school, fraction):
    """+fraction of the player's total spell power in one school (0.2 = +20%)."""
    return attr(f'spell_power:{school}', fraction, 'add_multiplied_total')


def sound(sound_id, pitch=1.0):
    return {'type': 'neoorigins:play_sound', 'sound': sound_id, 'volume': 1.0, 'pitch': pitch}


def particles(particle, count, spread=1.5, offset_y=1.0, speed=0.05):
    return {'type': 'neoorigins:spawn_particles', 'particle': particle, 'count': count, 'speed': speed,
            'offset_y': offset_y, 'spread': {'x': spread, 'y': 0.5, 'z': spread}}


def damage(amount, source='generic'):
    return {'type': 'neoorigins:damage', 'amount': amount, 'source': {'name': source}}


def effect(effect_id, seconds, amplifier=0):
    return {'type': 'neoorigins:apply_effect', 'effect': effect_id, 'duration': seconds * SECONDS,
            'amplifier': amplifier}


def foes_around(radius, actions, shape=None):
    """Runs actions on every non-player creature within radius of the caster."""
    aoe = {'type': 'neoorigins:area_of_effect', 'radius': radius, 'include_source': False,
           'entity_condition': NOT_PLAYER, 'entity_action': {'type': 'neoorigins:and', 'actions': actions}}
    if shape:
        aoe['shape'] = shape
    return aoe


def push_foes(radius, strength):
    return {'type': 'neoorigins:pull_entities', 'radius': radius, 'strength': -strength, 'include_players': False,
            'entity_condition': NOT_PLAYER}


def active(cooldown_s, icon, actions):
    return {'type': 'neoorigins:active_ability', 'cooldown_ticks': cooldown_s * SECONDS, 'cooldown_icon': icon,
            'entity_action': {'type': 'neoorigins:and', 'actions': actions}}


def size(scale):
    return {'type': 'neoorigins:size_scaling', 'scale': scale, 'modify_reach': False}


def damage_dealt(multiplier, condition):
    return {'type': 'neoorigins:modify_damage', 'direction': 'out', 'multiplier': multiplier, 'condition': condition}


def fire_taken(multiplier):
    return {'type': 'neoorigins:modify_damage', 'direction': 'in', 'damage_type': '#minecraft:is_fire',
            'multiplier': multiplier}


def trade_prices(multiplier):
    return {'type': 'neoorigins:action_on_event', 'event': 'mod_trade_price',
            'modifier': {'operation': 'multiplication', 'value': multiplier}}


# (key, name, description, power) per origin, in origin-screen order. Hidden companions (a second attribute of the
# same perk) have name None and are listed under the perk they belong to.
ORIGINS = {}

ORIGINS['hearthfolk'] = dict(
    name='Hearthfolk', icon='minecraft:bell', impact='low', order=1,
    description='Plain folk of the village lanes, quick on their feet and quicker with a deal. Where they raise a '
                'shout their friends stand taller, and the hearth always calls them home. Far from the Overworld '
                'they lose heart.',
    powers=[
        ('rally', 'Rally', 'Sound the call: you and players within 8 blocks gain Speed I, Resistance I and '
                           'Regeneration I for 10 s. Cooldown 90 s.',
         {**active(90, 'minecraft:bell', [
             {'type': 'neoorigins:area_of_effect', 'radius': 8.0, 'include_source': True,
              'entity_condition': {'type': 'neoorigins:entity_type', 'entity_type': 'minecraft:player'},
              'entity_action': {'type': 'neoorigins:and', 'actions': [
                  effect('minecraft:speed', 10), effect('minecraft:resistance', 10),
                  effect('minecraft:regeneration', 10)]}},
             sound('minecraft:block.bell.use'), particles('minecraft:happy_villager', 30)])}),
        ('hearthstone', 'Hearthstone', 'Return home to your bed (or the world spawn). Cooldown 30 min.',
         {'type': 'neoorigins:active_recall', 'cooldown_ticks': 30 * 60 * SECONDS, 'cooldown_icon': 'minecraft:campfire'}),
        ('light_step', 'Light Step', 'One extra combat roll charge.', attr('combat_roll:count', 1.0)),
        ('haggler', 'Haggler', 'Villager and wandering trader prices are about 25% lower.', trade_prices(0.75)),
        ('homebound', 'Homebound', 'Deals 15% less damage in the Nether and the End.',
         damage_dealt(0.85, {'type': 'neoorigins:not',
                             'condition': {'type': 'neoorigins:dimension', 'dimension': 'minecraft:overworld'}})),
    ])

ORIGINS['deepkin'] = dict(
    name='Deepkin', icon='minecraft:deepslate', impact='medium', order=2,
    description='Short, stout delvers raised in the deepslate dark. Their skin turns a blade like stone, whole ore '
                'veins give way to their picks and the ground shakes when they stamp. Under the open sky they '
                'feel small, and they sink like stones.',
    powers=[
        ('earthshatter', 'Earthshatter', 'Stamp the ground: creatures within 6 blocks take 8 damage and are thrown '
                                         'into the air. Cooldown 45 s.',
         active(45, 'minecraft:cracked_deepslate_bricks', [
             foes_around(6.0, [damage(8.0), {'type': 'neoorigins:add_velocity', 'y': 0.9}]),
             sound('minecraft:entity.generic.explode', 0.6), sound('minecraft:block.deepslate.break', 0.5),
             particles('minecraft:explosion', 6, spread=2.5, offset_y=0.2),
             particles('minecraft:campfire_cosy_smoke', 20, spread=3.0, offset_y=0.1, speed=0.02)])),
        ('vein_miner', 'Vein Miner', 'Sneak while mining an ore to break the whole connected vein (up to 32 '
                                     'blocks). Uses your tool for every block.', {'type': 'neoorigins:simple'}),
        ('stone_hide', 'Stone Hide', '+4 armor and +2 hearts.', attr('minecraft:generic.armor', 4.0)),
        (None, None, None, attr('minecraft:generic.max_health', 4.0)),
        ('delver', 'Delver', 'Mines 25% faster.', {'type': 'neoorigins:break_speed_modifier', 'multiplier': 1.25}),
        ('gloomsight', 'Gloomsight', 'Night vision while out of sight of the sky.',
         {'type': 'neoorigins:persistent_effect', 'toggleable': False, 'show_icon': False, 'show_particles': False,
          'condition': {'type': 'neoorigins:not', 'condition': {'type': 'neoorigins:exposed_to_sky'}},
          'effects': [{'effect': 'minecraft:night_vision', 'amplifier': 0}]}),
        ('earthbound', 'Earthbound', '+20% Earth spell power.', spell_bonus('earth', 0.2)),
        ('stocky', 'Stocky', '85% of normal height; reach is unchanged.', size(0.85)),
        ('heavy_bones', 'Heavy Bones', 'Swims 40% slower.', attr('neoforge:swim_speed', -0.4, 'add_multiplied_base')),
        ('sky_shy', 'Sky-shy', 'Deals 10% less damage under the open sky.',
         damage_dealt(0.9, {'type': 'neoorigins:exposed_to_sky'})),
    ])

ORIGINS['grovekin'] = dict(
    name='Grovekin', icon='minecraft:flowering_azalea', impact='low', order=3,
    description='Slender wanderers of the lush woods, sharp of eye and kin to every root and leaf. They climb any '
                'wall, mend what grows and bind what threatens it, but their frames are light and dry wood burns.',
    powers=[
        ('entangle', 'Entangle', 'Roots burst from the ground: creatures within 6 blocks are held in place for 5 s. '
                                 'Cooldown 90 s.',
         active(90, 'minecraft:hanging_roots', [
             foes_around(6.0, [effect('minecraft:slowness', 5, 5),
                               particles('minecraft:composter', 15, spread=0.5, offset_y=0.3)]),
             sound('minecraft:block.rooted_dirt.break', 0.6)])),
        ('wall_climb', 'Wall Climb', 'Climb any wall by walking into it.', {'type': 'neoorigins:wall_climbing'}),
        ('keen_eye', 'Keen Eye', '+15% ranged damage.', attr('ranged_weapon:damage', 0.15, 'add_multiplied_total')),
        ('windsong', 'Windsong', '+15% Air spell power.', spell_bonus('air', 0.15)),
        ('menders_touch', "Mender's Touch", '+15% Healing power.', spell_bonus('healing', 0.15)),
        ('forest_stride', 'Forest Stride', 'Moves 15% faster in forest biomes.',
         attr('minecraft:generic.movement_speed', 0.15, 'add_multiplied_base', location_condition={'biome_tag': 'minecraft:is_forest'})),
        ('slender', 'Slender', '90% of normal height; reach is unchanged.', size(0.9)),
        ('slight_frame', 'Slight Frame', '-2 hearts max health.', attr('minecraft:generic.max_health', -4.0)),
        ('dry_wood', 'Dry Wood', 'Takes 25% more fire damage.', fire_taken(1.25)),
    ])

ORIGINS['tuskborn'] = dict(
    name='Tuskborn', icon='minecraft:gilded_blackstone', impact='medium', order=4,
    description='Broad, tusked folk of the blackstone bastions. They charge first, hit hardest when bloodied and '
                'stand their ground, and the bastion guards still count them as kin. Magic sits poorly in them, '
                'and villagers count their coins twice.',
    powers=[
        ('charge', 'Charge', 'Rush forward, slamming creatures in front of you (up to 4 blocks) for 6 damage and '
                             'knocking them aside. Cooldown 20 s.',
         active(20, 'minecraft:goat_horn', [
             # The hit comes first: NeoOrigins' delay action only runs from the player's own tick, which is not
             # guaranteed to land where the dash ends, so the charge strikes what is in front, then rushes.
             foes_around(4.0, [damage(6.0), {'type': 'neoorigins:add_velocity', 'y': 0.3}],
                         shape={'type': 'cone', 'angle': 90}),
             push_foes(4.0, 1.5),
             {'type': 'neoorigins:dash', 'strength': 2.2, 'allow_vertical': False},
             sound('minecraft:entity.ravager.roar', 1.2), particles('minecraft:sweep_attack', 4, spread=1.0)])),
        ('battle_fury', 'Battle Fury', 'Blood up: Haste II and Strength I for 15 s. Cooldown 120 s.',
         active(120, 'minecraft:golden_axe', [
             effect('minecraft:haste', 15, 1), effect('minecraft:strength', 15),
             sound('minecraft:entity.piglin_brute.angry'), particles('minecraft:angry_villager', 6)])),
        ('bloodrage', 'Bloodrage', 'Below 30% health: Strength II and Resistance I.',
         {'type': 'neoorigins:low_hp_threshold', 'threshold': 0.3,
          'effects': [{'effect': 'minecraft:strength', 'amplifier': 1}, {'effect': 'minecraft:resistance', 'amplifier': 0}]}),
        ('brutal_strikes', 'Brutal Strikes', '+20% crit damage and +5% crit chance.',
         attr('critical_strike:damage', 0.2, 'add_multiplied_base')),
        (None, None, None, attr('critical_strike:chance', 0.05, 'add_multiplied_base')),
        ('planted', 'Planted', '+50% knockback resistance.', attr('minecraft:generic.knockback_resistance', 0.5)),
        ('bastion_kin', 'Bastion Kin', "Piglins leave you be unless you strike first (brutes still don't).",
         {'type': 'neoorigins:mobs_ignore_player', 'entity_types': ['minecraft:piglin']}),
        ('broad', 'Broad', '110% of normal height; still fits through doors.', size(1.1)),
        ('brute_mind', 'Brute Mind', '-20% spell power in every school.', spell_bonus(SPELL_SCHOOLS[0], -0.2)),
    ] + [(None, None, None, spell_bonus(s, -0.2)) for s in SPELL_SCHOOLS[1:]] + [
        ('hard_bargain', 'Hard Bargain', 'Villager and wandering trader prices are about 25% higher.', trade_prices(1.25)),
    ])

ORIGINS['emberkin'] = dict(
    name='Emberkin', icon='minecraft:blaze_powder', impact='high', order=5,
    description='Blaze-touched wanderers with cinders for blood. Flame and lava cannot hurt them, fire leaps from '
                'their hands and even death only rekindles them. Water burns them like acid, rain a little less.',
    powers=[
        ('fireball', 'Fireball', 'Hurl a ball of fire: creatures within 3 blocks of where it lands take 8 damage '
                                 'and burn for 4 s. It breaks no blocks. Cooldown 20 s.',
         active(20, 'minecraft:fire_charge', [
             {'type': 'neoorigins:spawn_projectile', 'entity_type': 'neoorigins:magic_orb', 'speed': 1.6,
              'orb_color': '#FF7A1A', 'glow_color': '#FFD24A', 'trail_particle': 'minecraft:flame',
              'on_hit_action': {'type': 'neoorigins:and', 'actions': [
                  foes_around(3.0, [damage(8.0, 'fire'), {'type': 'neoorigins:set_on_fire', 'ticks': 4 * SECONDS}]),
                  particles('minecraft:lava', 12, spread=1.0, offset_y=0.2),
                  sound('minecraft:entity.generic.explode', 1.3)]}},
             sound('minecraft:entity.blaze.shoot')])),
        ('phoenix', 'Phoenix', 'When you would die you burst into flame instead: creatures within 5 blocks take 6 '
                               'damage and burn, and you rise with 4 hearts. Once every 20 min.',
         {'type': 'neoorigins:prevent_death', 'set_health': 8.0, 'cooldown_ticks': 20 * 60 * SECONDS,
          'entity_action': {'type': 'neoorigins:and', 'actions': [
              foes_around(5.0, [damage(6.0, 'fire'), {'type': 'neoorigins:set_on_fire', 'ticks': 5 * SECONDS}]),
              effect('minecraft:regeneration', 5, 1),
              sound('minecraft:item.totem.use'), sound('minecraft:entity.blaze.shoot', 0.6),
              particles('minecraft:flame', 80, spread=2.0), particles('minecraft:lava', 20, spread=1.5)]}}),
        ('cinder_blood', 'Cinder Blood', 'Immune to fire and lava.', {'type': 'neoorigins:prevent_action', 'action': 'fire'}),
        ('kindled', 'Kindled', '+20% Fire spell power.', spell_bonus('fire', 0.2)),
        ('searing_strikes', 'Searing Strikes', 'Your hits set creatures alight for 3 s.',
         {'type': 'neoorigins:simple'}),
        ('lava_swimmer', 'Lava Swimmer', 'Swims through lava as easily as through water.',
         {'type': 'neoorigins:modify_lava_speed', 'operation': 'addition', 'value': 0.03}),
        ('doused', 'Doused', 'Takes 1 damage per second in water, and every 2 s in rain.',
         {'type': 'neoorigins:condition_passive', 'interval': 20, 'condition': {'type': 'neoorigins:in_water'},
          'entity_action': damage(1.0, 'drown')}),
        (None, None, None,
         {'type': 'neoorigins:condition_passive', 'interval': 40,
          'condition': {'type': 'neoorigins:and', 'conditions': [
              {'type': 'neoorigins:in_rain'}, {'type': 'neoorigins:not', 'condition': {'type': 'neoorigins:in_water'}}]},
          'entity_action': damage(1.0, 'drown')}),
    ])

ORIGINS['rimeborn'] = dict(
    name='Rimeborn', icon='minecraft:packed_ice', impact='medium', order=6,
    description='Pale wanderers of the ice spikes and the cold seas. Frost cannot bite them, water freezes under '
                'their feet and the tide answers their call. Heat saps them, and fire bites deep.',
    powers=[
        ('tidal_wave', 'Tidal Wave', 'A cone of icy water: creatures up to 8 blocks ahead take 5 damage, are '
                                     'thrown back and slowed for 4 s. Cooldown 30 s.',
         active(30, 'minecraft:heart_of_the_sea', [
             foes_around(8.0, [damage(5.0, 'freeze'), effect('minecraft:slowness', 4, 1),
                               {'type': 'neoorigins:add_velocity', 'y': 0.4},
                               particles('minecraft:splash', 12, spread=0.6, offset_y=0.5)],
                         shape={'type': 'cone', 'angle': 70}),
             # The push has no cone of its own: it throws back every creature within reach, not only those ahead.
             push_foes(8.0, 1.5),
             sound('minecraft:entity.player.splash.high_speed'), sound('minecraft:block.glass.break', 1.4),
             particles('minecraft:bubble_pop', 30, spread=2.0)])),
        ('frostwalker', 'Frostwalker', 'Walk on water as if it were ice. Sneak to sink.',
         {'type': 'neoorigins:walk_on_fluid', 'fluid': 'water',
          'condition': {'type': 'neoorigins:not', 'condition': {'type': 'neoorigins:sneaking'}}}),
        ('frostbound', 'Frostbound', 'Immune to freezing.', {'type': 'neoorigins:prevent_action', 'action': 'freeze'}),
        ('snowstride', 'Snowstride', 'Moves freely through powder snow.',
         {'type': 'neoorigins:no_slowdown', 'block_tag': 'minerpg:powder_snow'}),
        ('rime_heart', 'Rime Heart', '+20% Frost spell power and +15% Water spell power.', spell_bonus('frost', 0.2)),
        (None, None, None, spell_bonus('water', 0.15)),
        ('tideborn', 'Tideborn', 'Swims 30% faster and holds its breath twice as long.',
         attr('neoforge:swim_speed', 0.3, 'add_multiplied_base')),
        (None, None, None, attr('minecraft:generic.oxygen_bonus', 1.0)),
        ('chilling_strikes', 'Chilling Strikes', 'Your hits slow creatures for 2 s.',
         {'type': 'neoorigins:simple'}),
        ('heat_wilt', 'Heat Wilt', 'Weakness I in the Nether and in hot biomes (desert, badlands, savanna, jungle).',
         {'type': 'neoorigins:persistent_effect', 'toggleable': False,
          'condition': {'type': 'neoorigins:or', 'conditions': [
              {'type': 'neoorigins:dimension', 'dimension': 'minecraft:the_nether'},
              {'type': 'neoorigins:biome', 'tag': 'c:is_hot/overworld'}]},
          'effects': [{'effect': 'minecraft:weakness', 'amplifier': 0}]}),
        ('melting', 'Melting', 'Takes 25% more fire damage.', fire_taken(1.25)),
    ])

ORIGINS['voidborn'] = dict(
    name='Voidborn', icon='minecraft:ender_eye', impact='medium', order=7,
    description='Tall, quiet strangers from the far islands of the End. Raw arcane power hums in them, space folds '
                'when they step, the void keeps a pocket for them and the wind of the End carries their wings. '
                'Water burns them.',
    powers=[
        ('blink', 'Blink', 'Step through space to the block you are looking at, up to 12 blocks away. Cooldown 30 s.',
         {'type': 'neoorigins:active_teleport', 'range': 12.0, 'mode': 'target', 'cooldown_ticks': 30 * SECONDS,
          'cooldown_icon': 'minecraft:ender_pearl'}),
        ('void_surge', 'Void Surge', 'While gliding with an elytra, surge forward like a firework. Cooldown 20 s.',
         {'type': 'neoorigins:elytra_boost', 'strength': 1.5, 'cooldown_ticks': 20 * SECONDS,
          'cooldown_icon': 'minecraft:elytra'}),
        ('void_pocket', 'Void Pocket', '9 extra inventory slots only you can open. They are kept when you die.',
         {'type': 'neoorigins:extra_inventory', 'size': 9, 'drop_on_death': False, 'title': 'Void Pocket'}),
        ('void_hum', 'Void Hum', '+20% Arcane spell power.', spell_bonus('arcane', 0.2)),
        ('kindred_gaze', 'Kindred Gaze', "Endermen don't anger when you look at them.",
         {'type': 'neoorigins:ender_gaze_immunity'}),
        ('lanky', 'Lanky', '110% of normal height; still fits through doors.', size(1.1)),
        ('water_bane', 'Water Bane', 'Takes 1 damage per second in water.',
         {'type': 'neoorigins:condition_passive', 'interval': 20, 'condition': {'type': 'neoorigins:in_water'},
          'entity_action': damage(1.0, 'drown')}),
    ])

ORIGINS['gravebound'] = dict(
    name='Gravebound', icon='minecraft:soul_lantern', impact='medium', order=8,
    description='Risen from the soul sand valleys, neither living nor quite dead. They feed on the blows they '
                'land, rage without tiring, raise the dead to fight for them and can play dead themselves. Mortal '
                'remedies barely take.',
    powers=[
        ('raise_dead', 'Raise Dead', 'Two skeleton warriors rise to fight for you for 30 s. Cooldown 2 min.',
         {'type': 'neoorigins:summon_minion', 'mob_type': 'minecraft:skeleton', 'quantity': 2, 'max_count': 2,
          'cooldown_ticks': 120 * SECONDS, 'hunger_cost': 0, 'despawn_ticks': 30 * SECONDS, 'death_damage': 0.0,
          'head': 'minecraft:iron_helmet', 'mainhand': 'minecraft:iron_sword', 'cooldown_icon': 'minecraft:skeleton_skull'}),
        ('feign_death', 'Feign Death', 'Play dead: you turn invisible and every creature that was after you loses '
                                       'track of you. Cooldown 90 s.',
         active(90, 'minecraft:wither_rose', [
             effect('minecraft:invisibility', 5),
             {'type': 'neoorigins:kubejs_callback', 'id': 'minerpg:feign_death'},
             sound('minecraft:entity.skeleton.death', 0.8), particles('minecraft:soul', 20, spread=0.8)])),
        ('soul_leech', 'Soul Leech', '10% of all damage you deal heals you.', attr('mrpg_lib:lifesteal_modifier', 0.1, 'add_multiplied_base')),
        ('deathless_fury', 'Deathless Fury', '+20% Rage power.', attr('mrpg_lib:rage_modifier', 0.2, 'add_multiplied_base')),
        ('grave_hush', 'Grave Hush', 'Hostile creatures notice you from 40% closer than usual.',
         {'type': 'neoorigins:sneaky', 'detection_multiplier': 0.6}),
        ('hunched', 'Hunched', '95% of normal height; reach is unchanged.', size(0.95)),
        ('withered_vigor', 'Withered Vigor', 'All healing you receive (food, potions, spells) is 30% weaker.',
         {'type': 'neoorigins:action_on_event', 'event': 'mod_natural_regen',
          'modifier': {'operation': 'multiplication', 'value': 0.7}}),
    ])


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def main():
    if os.path.isdir(POWERS):
        shutil.rmtree(POWERS)
    total = 0
    for key, o in ORIGINS.items():
        ids = []
        last = None
        companion = 0
        for pkey, name, description, power in o['powers']:
            if pkey is None:
                # A hidden companion of the perk above it (the perk's second stat).
                companion += 1
                pid = f'{key}_{last}_{companion + 1}'
                body = {**power, 'hidden': True}
            else:
                last, companion = pkey, 0
                pid = f'{key}_{pkey}'
                body = {'type': power['type'], 'name': text(name), 'description': text(description),
                        **{k: v for k, v in power.items() if k != 'type'}}
            write(os.path.join(POWERS, pid + '.json'), body)
            ids.append(f'minerpg:{pid}')
            total += 1
        write(os.path.join(BASE, key + '.json'), {
            'name': text(o['name']), 'description': text(o['description']), 'icon': o['icon'],
            'impact': o['impact'], 'order': o['order'], 'powers': ids, 'upgrades': []})
    print(f'{len(ORIGINS)} origins, {total} powers -> {BASE}')


if __name__ == '__main__':
    main()
