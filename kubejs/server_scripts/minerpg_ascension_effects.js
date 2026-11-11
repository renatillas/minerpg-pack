// minerpg: Ascension effects that Spell Engine data can't express (pack 1.8.0).
// Design: docs/superpowers/specs/2026-11-11-minerpg-ascension-design.md. Talents are recognised by the player tag
// each Ascension skill gives (asc_<fate>_<node>, removed when the skill is locked or reset; see
// pack/tools/gen_ascension.py). Ultimate casts arrive through the player's persistent data, written by
// startup_scripts/minerpg_ascension.js (asc_cast_<spell path> = game time).
//
// Party safety: everything harmful here goes only to enemies (ascIsEnemy: monsters and other hostile mobs, never
// players or tamed animals).

const $AscRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const $AscRL = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $AscEffectInstance = Java.loadClass('net.minecraft.world.effect.MobEffectInstance')
const $AscModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
const $AscOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
const $AscPlayer = Java.loadClass('net.minecraft.world.entity.player.Player')
const $AscServerPlayer = Java.loadClass('net.minecraft.server.level.ServerPlayer')
const $AscLiving = Java.loadClass('net.minecraft.world.entity.LivingEntity')
const $AscEnemy = Java.loadClass('net.minecraft.world.entity.monster.Enemy')
const $AscIncoming = Java.loadClass('net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent')
const $AscHeal = Java.loadClass('net.neoforged.neoforge.event.entity.living.LivingHealEvent')
const $AscSpellRegistry = Java.loadClass('net.spell_engine.api.spell.registry.SpellRegistry')
const $AscParticles = Java.loadClass('net.minecraft.core.particles.ParticleTypes')

const ASC_VENOM = 'mrpg_lib:fatal_poison'

function ascHas(player, tag) {
  return player.getTags().contains(tag)
}

function ascEffect(id) {
  return $AscRegistries.MOB_EFFECT.getHolder($AscRL.parse(id)).get()
}

function ascAttribute(id) {
  return $AscRegistries.ATTRIBUTE.getHolder($AscRL.parse(id)).get()
}

function ascGive(entity, id, ticks, amplifier) {
  entity.addEffect(new $AscEffectInstance(ascEffect(id), ticks, amplifier))
}

function ascHasEffect(entity, id) {
  return entity.hasEffect(ascEffect(id))
}

function ascAmplifier(entity, id) {
  var e = entity.getEffect(ascEffect(id))
  return e == null ? -1 : e.getAmplifier()
}

function ascIsEnemy(entity) {
  return entity instanceof $AscLiving && entity instanceof $AscEnemy && !(entity instanceof $AscPlayer) && entity.isAlive()
}

function ascEnemiesNear(entity, radius) {
  var box = entity.getBoundingBox().inflate(radius)
  return entity.level.getEntitiesOfClass($AscLiving, box).filter(e => ascIsEnemy(e) && e.distanceTo(entity) <= radius)
}

function ascPlayersNear(entity, radius) {
  var box = entity.getBoundingBox().inflate(radius)
  return entity.level.getEntitiesOfClass($AscServerPlayer, box).filter(p => !p.isSpectator() && p.distanceTo(entity) <= radius)
}

function ascNow(entity) {
  return entity.level.getLevelData().getGameTime()
}

// A cast of an Ascension spell this tick or within `window` ticks (see the startup script).
function ascCastWithin(player, path, window) {
  var data = player.getPersistentData()
  if (!data.contains('asc_cast_' + path)) return false
  return ascNow(player) - data.getLong('asc_cast_' + path) <= window
}

// A cast not handled yet: true once per cast.
function ascNewCast(player, path) {
  var data = player.getPersistentData()
  if (!data.contains('asc_cast_' + path)) return false
  var at = data.getLong('asc_cast_' + path)
  if (data.getLong('asc_seen_' + path) == at) return false
  data.putLong('asc_seen_' + path, at)
  return true
}

function ascTimerSet(player, name, ticks) {
  player.getPersistentData().putLong('asc_until_' + name, ascNow(player) + ticks)
}

function ascTimerOn(player, name) {
  return player.getPersistentData().getLong('asc_until_' + name) > ascNow(player)
}

// Temporary stat changes (Killing Rhythm, Momentum, ...): a transient attribute modifier with an end time. Transient
// modifiers are not saved, so a relog also ends them. `flat` adds the amount instead of a percentage of the base (for
// stats whose base is 0, like knockback resistance).
function ascTimedModifier(player, name, attribute, amount, ticks, flat) {
  var inst = player.getAttribute(ascAttribute(attribute))
  if (inst == null) return
  var id = $AscRL.parse('minerpg:asc_' + name)
  // removeModifier is overloaded (id / modifier); Rhino needs the one named.
  inst['removeModifier(net.minecraft.resources.ResourceLocation)'](id)
  inst.addTransientModifier(new $AscModifier(id, amount, flat ? $AscOperation.ADD_VALUE : $AscOperation.ADD_MULTIPLIED_BASE))
  var data = player.getPersistentData()
  data.putLong('asc_mod_' + name, ascNow(player) + ticks)
  data.putString('asc_modattr_' + name, attribute)
}

function ascExpireModifiers(player) {
  var data = player.getPersistentData()
  var now = ascNow(player)
  data.getAllKeys().forEach(key => {
    key = String(key)
    if (key.indexOf('asc_mod_') != 0 || data.getLong(key) > now) return
    var name = key.substring('asc_mod_'.length)
    var inst = player.getAttribute(ascAttribute(String(data.getString('asc_modattr_' + name))))
    if (inst != null) inst['removeModifier(net.minecraft.resources.ResourceLocation)']($AscRL.parse('minerpg:asc_' + name))
    data.remove(key)
  })
}

function ascSpellHolder(level, id) {
  return $AscSpellRegistry.from(level).getHolder($AscRL.parse(id))
}

// Spell Engine cooldowns: reset one spell, or take seconds off it.
function ascResetCooldown(player, id) {
  var manager = player.getCooldownManager()
  manager.reset($AscRL.parse(id))
  manager.pushSync()
}

function ascShortenCooldown(player, id, ticks) {
  var holder = ascSpellHolder(player.level, id)
  if (!holder.isPresent()) return
  var manager = player.getCooldownManager()
  var left = manager.getCooldownDuration(holder.get())
  manager.setDurationLeft(holder.get(), Math.max(0, left - ticks))
  manager.pushSync()
}

function ascBurst(entity, particle, count, spread) {
  entity.level.sendParticles(particle, entity.getX(), entity.getY() + 1.0, entity.getZ(), count, spread, 0.5, spread, 0.05)
}

// ------------------------------------------------------------------------------------------------------------------
// Rogue: Nightblade, Plaguefang
// ------------------------------------------------------------------------------------------------------------------
const ASC_AMBUSH_MULTIPLIER = 2.5
const ASC_BLOOM = 'ascension_plaguefang_ultimate'
const ASC_CUTS = 'ascension_nightblade_ultimate'

function ascBloomRadius(player) {
  return ascHas(player, 'asc_plaguefang_emp_dragon') ? 7.5 : 5.0
}

// ------------------------------------------------------------------------------------------------------------------
// Warrior: Juggernaut, Reaver. Priest: Lightbinder, Zealot. Paladin: Bulwark, Crusader.
// ------------------------------------------------------------------------------------------------------------------
const ASC_COLOSSUS = 'ascension_juggernaut_ultimate'
const ASC_RAMPAGE = 'ascension_reaver_ultimate'
const ASC_DAWNFALL = 'ascension_lightbinder_ultimate'
const ASC_WRATH = 'ascension_zealot_ultimate'
const ASC_BASTION = 'ascension_bulwark_ultimate'
const ASC_AVATAR = 'ascension_crusader_ultimate'
const ASC_RULES = JsonIO.read('kubejs/ascension/rules.json')

function ascIsHoly(source) {
  var key = source.typeHolder().unwrapKey()
  return key.isPresent() && String(key.get().location()) == 'spell_power:healing'
}

function ascHealingPower(player) {
  var inst = player.getAttribute(ascAttribute('spell_power:healing'))
  return inst == null ? 0 : inst.getValue()
}

// Fate holy-damage corrections (rules.json, computed by gen_ascension.py): holy damage and healing are one stat.
function ascHolyMultiplier(player) {
  var m = 1.0
  if (ASC_RULES == null) return m
  var table = ASC_RULES.holy_damage_multiplier
  for (var tag in table) if (ascHas(player, String(tag))) m *= Number(table[tag])
  return m
}

// Extra hits from Ascension effects (shockwaves, Cleave, Hallowed Ground, ...). They must not trigger on-hit effects
// again: a shockwave from enemy A to enemy B would shock A back, forever (the event fires before damage immunity).
var ascInternalHit = false

function ascMagicHit(target, player, amount) {
  ascInternalHit = true
  try {
    target.attack(player.damageSources().indirectMagic(player, player), amount)
  } finally {
    ascInternalHit = false
  }
}

// A weapon swing (not a spell, arrow or effect).
function ascIsMelee(source) {
  var key = source.typeHolder().unwrapKey()
  return key.isPresent() && String(key.get().location()) == 'minecraft:player_attack'
}

function ascMostInjuredNear(player, radius) {
  var best = null
  ascPlayersNear(player, radius).forEach(p => {
    if (p.getHealth() >= p.getMaxHealth()) return
    if (best == null || p.getHealth() / p.getMaxHealth() < best.getHealth() / best.getMaxHealth()) best = p
  })
  return best
}

// ------------------------------------------------------------------------------------------------------------------
// Damage dealt by players to enemies (multipliers, on-hit effects).
function ascOutgoing(event, attacker, victim) {
  if (ascInternalHit) return
  var source = event.getSource()
  var direct = source.getImmediate() == attacker
  var melee = direct && ascIsMelee(source)
  var holy = ascIsHoly(source)
  var amount = event.getAmount()

  // Nightblade: Ambush (and Exposed Throat).
  if (melee && ascHas(attacker, 'asc_nightblade_fate') &&
      (ascHasEffect(attacker, 'rogues:stealth') || ascHasEffect(attacker, 'rogues:shadow_step'))) {
    amount *= ASC_AMBUSH_MULTIPLIER
    ascBurst(victim, $AscParticles.CRIT, 20, 0.4)
    if (ascHas(attacker, 'asc_nightblade_deep_2')) ascGive(victim, 'rogues:shatter', 100, 1)
  }
  // Plaguefang: Numbing Agent.
  if (ascHas(attacker, 'asc_plaguefang_deep_2') && ascAmplifier(victim, ASC_VENOM) >= 2) {
    ascGive(victim, 'minecraft:slowness', 40, 1)
  }
  // Reaver: Scent of Blood.
  if (melee && ascHas(attacker, 'asc_reaver_deep_3') && victim.getHealth() < victim.getMaxHealth() / 2) amount *= 1.15
  // Holy damage: Fate corrections, Smite the Wicked.
  if (holy) {
    amount *= ascHolyMultiplier(attacker)
    if (ascHas(attacker, 'asc_zealot_deep_3') && victim.isInvertedHealAndHarm()) amount *= 1.25
  }
  // Crusader: Blessed Arms (extra holy damage on melee hits), Avatar of Light (+30%).
  if (melee && ascHas(attacker, 'asc_crusader_fate')) amount += 0.3 * ascHealingPower(attacker)
  if (melee && ascTimerOn(attacker, 'avatar')) amount *= 1.3
  event.setAmount(amount)

  // After-hit effects.
  if (holy && ascHas(attacker, 'asc_zealot_fate')) {
    var ally = ascMostInjuredNear(attacker, 12)
    if (ally != null) ally.heal(amount * 0.4)
  }
  if (holy && ascHas(attacker, 'asc_zealot_deep_1')) {
    var data = attacker.getPersistentData()
    var stacks = ascTimerOn(attacker, 'fervor') ? Math.min(5, data.getInt('asc_fervor') + 1) : 1
    data.putInt('asc_fervor', stacks)
    ascTimerSet(attacker, 'fervor', 100)
    ascTimedModifier(attacker, 'fervor', 'spell_power:haste', 0.03 * stacks, 100)
  }
  // Reaver: Bloodletting and Cleave (the hit right after a Mortal Strike cast).
  if (direct && ascCastWithin(attacker, 'mortal_strike', 12)) {
    if (ascHas(attacker, 'asc_reaver_trans_2')) attacker.heal(amount * 0.2)
    if (ascHas(attacker, 'asc_reaver_deep_2')) {
      ascEnemiesNear(victim, 2.5).forEach(e => {
        if (e != victim) ascMagicHit(e, attacker, amount * 0.5)
      })
    }
  }
  if (ascTimerOn(attacker, 'rampage') && ascHas(attacker, 'asc_reaver_emp_dragon')) attacker.heal(amount * 0.15)
  // Crusader: Light's Reprisal, Avatar of Light's shockwave and Shared Radiance.
  if (melee && ascHas(attacker, 'asc_crusader_deep_3')) attacker.heal(amount * 0.03)
  if (melee && ascTimerOn(attacker, 'avatar')) {
    ascEnemiesNear(victim, 3).forEach(e => {
      if (e != victim) ascMagicHit(e, attacker, amount * 0.3)
    })
    ascBurst(victim, $AscParticles.END_ROD, 20, 1.5)
    if (ascHas(attacker, 'asc_crusader_emp_wither')) {
      ascPlayersNear(attacker, 8).forEach(p => {
        if (p != attacker) p.heal(amount * 0.02)
      })
    }
  }
}

// Damage taken by players.
function ascIncoming(event, victim) {
  var attacker = event.getSource().getActual()
  var amount = event.getAmount()
  // Juggernaut: Iron Hide, Colossus (-50% with its Resistance II counted: 0.6 * 0.8333 = 0.5).
  if (ascHas(victim, 'asc_juggernaut_deep_1') && victim.getHealth() > victim.getMaxHealth() / 2) amount *= 0.9
  if (ascTimerOn(victim, 'colossus')) amount *= 0.8333
  // Allies' auras: Bulwark of Giants (Colossus), Sanctuary, Bastion of Light.
  ascPlayersNear(victim, 8).forEach(p => {
    if (p == victim) return
    if (ascHas(p, 'asc_juggernaut_emp_dragon') && ascTimerOn(p, 'colossus')) amount *= 0.8
    if (ascHas(p, 'asc_lightbinder_deep_3') && p.distanceTo(victim) <= 6) amount *= 0.92
  })
  if (ascInBastion(victim)) amount *= 0.4
  event.setAmount(amount)
  // Juggernaut: Unbroken reflects 30% at the attacker.
  if (attacker != null && ascIsEnemy(attacker) && ascTimerOn(victim, 'unbroken')) ascMagicHit(attacker, victim, amount * 0.3)
}

NativeEvents.onEvent($AscIncoming, event => {
  var victim = event.getEntity()
  var attacker = event.getSource().getActual()
  if (victim instanceof $AscServerPlayer) {
    ascIncoming(event, victim)
  } else if (attacker instanceof $AscServerPlayer && !(victim instanceof $AscPlayer)) {
    ascOutgoing(event, attacker, victim)
  }
})

// ------------------------------------------------------------------------------------------------------------------
// Kills.
EntityEvents.death(event => {
  var victim = event.getEntity()
  if (victim instanceof $AscPlayer) {
    ascDeathSave(event, victim)
    return
  }
  var killer = event.getSource().player

  if (killer != null && killer instanceof $AscServerPlayer) {
    // Nightblade: Severing Step (Shadow Step's mark lasts 3 s with the transformation), Killing Rhythm, Endless Cuts.
    if (ascHas(killer, 'asc_nightblade_trans_1') && ascHasEffect(killer, 'rogues:shadow_step')) {
      ascResetCooldown(killer, 'rogues:shadow_step')
    }
    if (ascHas(killer, 'asc_nightblade_deep_1')) {
      ascGive(killer, 'minecraft:speed', 80, 1)
      ascTimedModifier(killer, 'killing_rhythm', 'minecraft:generic.attack_speed', 0.25, 80)
    }
    if (ascHas(killer, 'asc_nightblade_emp_wither') && ascCastWithin(killer, ASC_CUTS, 10)) {
      ascShortenCooldown(killer, 'minerpg:' + ASC_CUTS, 200)
    }
    // Plaguefang: Virulence.
    var venom = ascAmplifier(victim, ASC_VENOM)
    if (venom >= 0 && ascHas(killer, 'asc_plaguefang_deep_1')) {
      var next = ascEnemiesNear(victim, 6).filter(e => e != victim)
      next.sort((a, b) => a.distanceTo(victim) - b.distanceTo(victim))
      if (next.length > 0) ascGive(next[0], ASC_VENOM, 120, venom)
    }
    // Reaver: Finisher resets Charge; Momentum; Rampage resets every cooldown (No End adds 1 s).
    if (ascHas(killer, 'asc_reaver_fate')) ascResetCooldown(killer, 'rogues:charge')
    if (ascHas(killer, 'asc_reaver_deep_1')) {
      var kdata = killer.getPersistentData()
      var stacks = ascTimerOn(killer, 'momentum') ? Math.min(3, kdata.getInt('asc_momentum') + 1) : 1
      kdata.putInt('asc_momentum', stacks)
      ascTimerSet(killer, 'momentum', 120)
      ascTimedModifier(killer, 'momentum', 'minecraft:generic.attack_speed', 0.1 * stacks, 120)
    }
    if (ascTimerOn(killer, 'rampage')) {
      var manager = killer.getCooldownManager()
      manager.spellsOnCooldown().forEach(id => {
        if (String(id) != 'minerpg:' + ASC_RAMPAGE) manager.reset(id)
      })
      manager.pushSync()
      if (ascHas(killer, 'asc_reaver_emp_wither')) {
        killer.getPersistentData().putLong('asc_until_rampage', killer.getPersistentData().getLong('asc_until_rampage') + 20)
      }
    }
    // Crusader: Zeal.
    if (ascHas(killer, 'asc_crusader_deep_1')) ascTimedModifier(killer, 'zeal', 'minecraft:generic.attack_speed', 0.2, 60)
  }
  // Plaguefang: Corpse Burst (any enemy dying inside a Wither-empowered Plague Bloom).
  if (victim instanceof $AscEnemy) {
    ascPlayersNear(victim, 7.5).forEach(player => {
      if (!ascHas(player, 'asc_plaguefang_emp_wither') || !ascTimerOn(player, 'bloom')) return
      if (player.distanceTo(victim) > ascBloomRadius(player)) return
      ascEnemiesNear(victim, 4).forEach(e => {
        if (e != victim) ascGive(e, ASC_VENOM, 120, 4)
      })
      ascBurst(victim, $AscParticles.SNEEZE, 30, 1.5)
    })
  }
})

// Lightbinder: Dawnfall's ward holds an ally at 1 health once.
function ascDeathSave(event, player) {
  var data = player.getPersistentData()
  if (data.getLong('asc_until_ward') <= ascNow(player)) return
  data.remove('asc_until_ward')
  player.setHealth(1.0)
  ascBurst(player, $AscParticles.TOTEM_OF_UNDYING, 40, 0.6)
  event.cancel()
}

// A player's health just before each heal, for the Lightbinder heal hooks in startup_scripts/minerpg_ascension.js
// (Spell Engine reports heals after applying them).
NativeEvents.onEvent($AscHeal, event => {
  var entity = event.getEntity()
  if (entity instanceof $AscServerPlayer) entity.getPersistentData().putFloat('asc_pre_heal', entity.getHealth())
})

// ------------------------------------------------------------------------------------------------------------------
// Every tick: casts, auras, timers. One function per class, so the scratch-server probes can drive a test player
// (test players are not in the player list and don't tick).
function ascTickRogue(player, now) {
  // Nightblade: Smoke Exit (when Vanish ends).
  if (ascHas(player, 'asc_nightblade_trans_2')) {
    var hidden = ascHasEffect(player, 'rogues:stealth')
    var data = player.getPersistentData()
    if (data.getBoolean('asc_was_hidden') && !hidden) {
      ascEnemiesNear(player, 4).forEach(e => {
        ascGive(e, 'minecraft:blindness', 40, 0)
        ascGive(e, 'minecraft:slowness', 40, 2)
      })
      ascBurst(player, $AscParticles.LARGE_SMOKE, 40, 2.0)
    }
    data.putBoolean('asc_was_hidden', hidden)
  }
  // Plaguefang: Inured.
  if (now % 10 == 0 && ascHas(player, 'asc_plaguefang_deep_3')) {
    player.removeEffect(ascEffect('minecraft:poison'))
    player.removeEffect(ascEffect(ASC_VENOM))
  }
  // Plaguefang: Plague Bloom (8 s), one pulse a second.
  if (ascNewCast(player, ASC_BLOOM)) ascTimerSet(player, 'bloom', 160)
  if (now % 20 == 0 && ascTimerOn(player, 'bloom')) ascBloomPulse(player)
}

function ascBloomPulse(player) {
  var inside = ascEnemiesNear(player, ascBloomRadius(player))
  inside.forEach(e => {
    ascGive(e, ASC_VENOM, 120, Math.min(4, ascAmplifier(e, ASC_VENOM) + 1))
    ascGive(e, 'minecraft:weakness', 40, 0)
  })
  if (ascHas(player, 'asc_plaguefang_emp_dragon') && inside.length > 0) player.heal(inside.length)
  ascBurst(player, $AscParticles.SNEEZE, 40, ascBloomRadius(player) / 2)
}

function ascTickWarrior(player, now) {
  // Juggernaut: Charge pulls aggro and knocks enemies aside (1.5 s after the cast).
  if (ascHas(player, 'asc_juggernaut_fate')) {
    if (ascNewCast(player, 'charge')) ascTimerSet(player, 'charge', 30)
    if (ascTimerOn(player, 'charge')) {
      ascEnemiesNear(player, 2.5).forEach(e => {
        if (e.setTarget) e.setTarget(player)
        e.knockback(0.6, player.getX() - e.getX(), player.getZ() - e.getZ())
      })
    }
  }
  // Juggernaut: Unbroken (as long as Last Stand), Rallying Cry.
  if (ascHas(player, 'asc_juggernaut_trans_1') && ascNewCast(player, 'last_stand')) {
    var stand = player.getEffect(ascEffect('rogues:last_stand'))
    ascTimerSet(player, 'unbroken', stand == null ? 200 : stand.getDuration())
  }
  if (now % 10 == 0 && ascTimerOn(player, 'unbroken')) {
    ascEnemiesNear(player, 8).forEach(e => { if (e.setTarget) e.setTarget(player) })
  }
  if (ascHas(player, 'asc_juggernaut_trans_2') && ascNewCast(player, 'shout')) {
    // Absorption I: a 4-point barrier for 8 seconds (absorption needs the effect's max-absorption room).
    ascPlayersNear(player, 8).forEach(p => ascGive(p, 'minecraft:absorption', 160, 0))
  }
  // Juggernaut: Colossus (10 s), Earthshaker at the end.
  if (ascNewCast(player, ASC_COLOSSUS)) {
    ascTimerSet(player, 'colossus', 200)
    ascTimedModifier(player, 'colossus_scale', 'minecraft:generic.scale', 0.3, 200)
    ascTimedModifier(player, 'colossus_knockback', 'minecraft:generic.knockback_resistance', 1.0, 200, true)
    player.getPersistentData().putBoolean('asc_colossus_on', true)
  }
  var data = player.getPersistentData()
  if (data.getBoolean('asc_colossus_on') && !ascTimerOn(player, 'colossus')) {
    data.putBoolean('asc_colossus_on', false)
    if (ascHas(player, 'asc_juggernaut_emp_wither')) {
      ascEnemiesNear(player, 6).forEach(e => ascGive(e, 'rogues:shock', 40, 0))
      ascBurst(player, $AscParticles.EXPLOSION, 6, 3.0)
    }
  }
  // Reaver: Rampage (8 s).
  if (ascNewCast(player, ASC_RAMPAGE)) ascTimerSet(player, 'rampage', 160)
}

function ascTickPriest(player, now) {
  // Lightbinder: Living Barrier heals allies near your Barrier.
  if (now % 20 == 0 && ascHas(player, 'asc_lightbinder_trans_1')) {
    var box = player.getBoundingBox().inflate(16)
    player.level.getEntities(player, box).forEach(e => {
      // KubeJS hands the entity type to scripts as its id.
      if (String(e.getType()) != 'paladins:barrier') return
      ascPlayersNear(e, 3).forEach(p => p.heal(1.0 + 0.1 * ascHealingPower(player)))
    })
  }
  // Lightbinder: Dawnfall (8 s, 12 with Long Dawn): wards allies; First Light cleanses; Long Dawn heals 5%/s.
  if (ascNewCast(player, ASC_DAWNFALL)) {
    var ticks = ascHas(player, 'asc_lightbinder_emp_wither') ? 240 : 160
    ascTimerSet(player, 'dawn', ticks)
    ascPlayersNear(player, 12).forEach(p => {
      ascTimerSet(p, 'ward', ticks)
      if (ascHas(player, 'asc_lightbinder_emp_dragon')) {
        // Collect first: removing while walking the live effect map throws.
        var harmful = []
        p.getActiveEffects().forEach(inst => {
          if (!inst.getEffect().value().isBeneficial()) harmful.push(inst.getEffect())
        })
        harmful.forEach(effect => p.removeEffect(effect))
      }
    })
  }
  if (now % 20 == 0 && ascTimerOn(player, 'dawn') && ascHas(player, 'asc_lightbinder_emp_wither')) {
    ascPlayersNear(player, 12).forEach(p => p.heal(p.getMaxHealth() * 0.05))
  }
  // Zealot: Hallowed Ground under Holy Beam's target (4 s).
  if (ascHas(player, 'asc_zealot_trans_2') && ascNewCast(player, 'holy_beam')) {
    var target = player.level.getEntity(player.getPersistentData().getInt('asc_cast_target_holy_beam'))
    if (target != null) {
      var d = player.getPersistentData()
      d.putDouble('asc_ground_x', target.getX())
      d.putDouble('asc_ground_y', target.getY())
      d.putDouble('asc_ground_z', target.getZ())
      ascTimerSet(player, 'ground', 80)
    }
  }
  if (now % 20 == 0 && ascTimerOn(player, 'ground')) {
    var g = player.getPersistentData()
    var gx = g.getDouble('asc_ground_x'), gy = g.getDouble('asc_ground_y'), gz = g.getDouble('asc_ground_z')
    player.level.sendParticles($AscParticles.END_ROD, gx, gy + 0.2, gz, 20, 1.2, 0.1, 1.2, 0.02)
    ascEnemiesNear(player, 40).forEach(e => {
      if (e.distanceToSqr(gx, gy, gz) <= 6.25) ascMagicHit(e, player, 1.0 + 0.3 * ascHealingPower(player))
    })
  }
  // Zealot: Wrath of Dawn: 5 (9) pillars over 3 seconds.
  if (ascNewCast(player, ASC_WRATH)) {
    player.getPersistentData().putInt('asc_pillars', ascHas(player, 'asc_zealot_emp_wither') ? 9 : 5)
    ascTimerSet(player, 'wrath', 60)
  }
  var pillars = player.getPersistentData().getInt('asc_pillars')
  if (pillars > 0 && now % 6 == 0) {
    var foes = ascEnemiesNear(player, 10)
    if (foes.length == 0 || !ascTimerOn(player, 'wrath')) {
      player.getPersistentData().putInt('asc_pillars', 0)
    } else {
      var foe = foes[Math.floor(Math.random() * foes.length)]
      ascMagicHit(foe, player, 2.0 + 0.8 * ascHealingPower(player))
      if (ascHas(player, 'asc_zealot_emp_dragon')) ascGive(foe, 'rogues:shock', 20, 0)
      player.level.sendParticles($AscParticles.END_ROD, foe.getX(), foe.getY() + 1.5, foe.getZ(), 40, 0.2, 1.5, 0.2, 0.01)
      ascPlayersNear(foe, 4).forEach(p => p.heal(1.0 + 0.3 * ascHealingPower(player)))
      player.getPersistentData().putInt('asc_pillars', pillars - 1)
    }
  }
}

// A player inside any active Bastion of Light dome (radius 4).
function ascInBastion(player) {
  var inside = false
  ascPlayersNear(player, 4).forEach(p => {
    if (!ascTimerOn(p, 'bastion')) return
    var d = p.getPersistentData()
    if (player.distanceToSqr(d.getDouble('asc_dome_x'), d.getDouble('asc_dome_y'), d.getDouble('asc_dome_z')) <= 16) inside = true
  })
  return inside
}

function ascTickPaladin(player, now) {
  // Bulwark: Shared Protection.
  if (ascHas(player, 'asc_bulwark_trans_1') && ascNewCast(player, 'divine_protection')) {
    var guard = player.getEffect(ascEffect('paladins:divine_protection'))
    ascPlayersNear(player, 6).forEach(p => {
      if (p != player) ascGive(p, 'paladins:divine_protection', guard == null ? 160 : guard.getDuration(), 0)
    })
  }
  // Bulwark: Bastion of Light (8 s, radius 4 around where it was cast).
  if (ascNewCast(player, ASC_BASTION)) {
    var d = player.getPersistentData()
    d.putDouble('asc_dome_x', player.getX())
    d.putDouble('asc_dome_y', player.getY())
    d.putDouble('asc_dome_z', player.getZ())
    ascTimerSet(player, 'bastion', 160)
  }
  if (now % 20 == 0 && ascTimerOn(player, 'bastion')) {
    var dome = player.getPersistentData()
    var dx = dome.getDouble('asc_dome_x'), dy = dome.getDouble('asc_dome_y'), dz = dome.getDouble('asc_dome_z')
    player.level.sendParticles($AscParticles.END_ROD, dx, dy + 1, dz, 60, 2.5, 1.2, 2.5, 0.01)
    ascEnemiesNear(player, 12).forEach(e => {
      if (e.distanceToSqr(dx, dy, dz) > 16) return
      ascGive(e, 'minecraft:slowness', 30, 2)
      if (ascHas(player, 'asc_bulwark_emp_wither')) {
        e.igniteForSeconds(2)
        ascMagicHit(e, player, 1.0 + 0.2 * ascHealingPower(player))
      }
    })
    if (ascHas(player, 'asc_bulwark_emp_dragon')) {
      ascPlayersNear(player, 12).forEach(p => {
        if (p.distanceToSqr(dx, dy, dz) <= 16) p.heal(2.0)
      })
    }
  }
  // Crusader: Avenger's Leap (to Judgement's target), Avatar of Light (10 s).
  if (ascHas(player, 'asc_crusader_trans_1') && ascNewCast(player, 'judgement')) {
    var target = player.level.getEntity(player.getPersistentData().getInt('asc_cast_target_judgement'))
    if (target != null && ascIsEnemy(target) && player.distanceTo(target) <= 16) {
      player.teleportTo(target.getX(), target.getY(), target.getZ())
      ascBurst(player, $AscParticles.END_ROD, 30, 1.0)
    }
  }
  if (ascNewCast(player, ASC_AVATAR)) {
    ascTimerSet(player, 'avatar', 200)
    if (ascHas(player, 'asc_crusader_emp_dragon')) {
      ascGive(player, 'minecraft:slow_falling', 200, 0)
      ascGive(player, 'minecraft:jump_boost', 200, 1)
    }
  }
  if (now % 10 == 0 && ascTimerOn(player, 'avatar')) ascBurst(player, $AscParticles.END_ROD, 6, 0.6)
}

function ascTickPlayer(player) {
  var now = ascNow(player)
  ascExpireModifiers(player)
  ascTickRogue(player, now)
  ascTickWarrior(player, now)
  ascTickPriest(player, now)
  ascTickPaladin(player, now)
}

ServerEvents.tick(event => {
  event.server.getPlayerList().getPlayers().forEach(player => ascTickPlayer(player))
})
