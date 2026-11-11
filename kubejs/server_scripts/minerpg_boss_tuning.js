// minerpg: boss baseline tuning that the mods' own configs can't do (pack 0.8.0).
// Bosses are built for a full party of four and do NOT scale with the number of players
// (ScalingMobs was removed in 0.8.0). Cataclysm and Mowzie's Mobs bosses get their health,
// damage and damage limits from their own configs (config/cataclysm-common.toml,
// config/mowziesmobs-common.toml). This script does two things those configs can't:
//   1. The Wither and the Ender Dragon (no config), and the pack 1.5.2 boss mods: more health when they appear,
//      harder hits.
//   2. In-fight regeneration for a few bosses, so a lone, well-geared player can't simply
//      out-last them. A party of four out-damages the regeneration easily; one player can't.
// Numbers and reasoning: research_notes/Pack integration/balance_study_v2.md and
// docs/superpowers/specs/2026-10-30-minerpg-boss-balance-and-feel.md ("Boss balance implementation notes").
//
// Pack 1.8.0: OFF (BT_ENABLED). The designer wants to playtest every boss at its mods' default strength, so the boss
// configs are back to the mods' defaults too (cataclysm-common.toml, mowziesmobs-common.toml, the health values in
// bosses_of_mass_destruction.json5; the tuned versions are in git history before 1.8.0). The tables stay for when
// tuning comes back. While it is off, a boss saved with the old tuning (max health and attack damage are stored with
// the entity, e.g. a Cataclysm boss waiting in its lair) is put back to its type's current default when it loads.
const BT_ENABLED = false

const $BTAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const $BTModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
const $BTOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
const $BTResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $BTEntityType = Java.loadClass('net.minecraft.world.entity.EntityType')
const $BTIncomingDamage = Java.loadClass('net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent')
const $BTHeal = Java.loadClass('net.neoforged.neoforge.event.entity.living.LivingHealEvent')
const $BTJoin = Java.loadClass('net.neoforged.neoforge.event.entity.EntityJoinLevelEvent')

// health: max health multiplier. damage: multiplier on every hit the boss deals (its melee,
// skulls, fireballs and breath all name the boss as the attacker).
const BT_VANILLA_BOSSES_TUNED = {
  'minecraft:wither': { health: 53.75, damage: 5.0 },
  'minecraft:ender_dragon': { health: 22.25, damage: 2.5 },
  // Bosses'Rise (pack 1.5.2; its config caps health at 1024): Chapter 1 Sandworm 750 and Yeti 900 (like the Amethyst
  // Crab), late Chapter 1 Kraken and Infernal Dragon 3500 (like the Wildlands bosses), Chapter 2 Underworld Knight
  // 5000 (like the Harbinger). Multipliers on the bosses' built-in health (150/250/250/500/250; checked on the scratch
  // server: its config's health values don't change max health).
  'block_factorys_bosses:sandworm': { health: 5.0, damage: 2.0 },
  'block_factorys_bosses:yeti': { health: 3.6, damage: 1.2 },
  'block_factorys_bosses:infernal_dragon': { health: 14.0, damage: 2.0 },
  'block_factorys_bosses:kraken': { health: 7.0, damage: 3.0 },
  'block_factorys_bosses:underworld_knight': { health: 20.0, damage: 2.7 },
  // The Graveyard's Corrupted Champion (pack 1.5.5): 400 -> 3500, late Chapter 1 like the Kraken and the Dragon.
  'graveyard:lich': { health: 8.75, damage: 2.0 },
  // Bosses of Mass Destruction: health is in its own config (config/bosses_of_mass_destruction.json5); hits doubled.
  'bosses_of_mass_destruction:lich': { health: 1.0, damage: 2.0 },
  'bosses_of_mass_destruction:gauntlet': { health: 1.0, damage: 2.0 },
  'bosses_of_mass_destruction:obsidilith': { health: 1.0, damage: 2.0 },
  'bosses_of_mass_destruction:void_blossom': { health: 1.0, damage: 2.0 },
}
const BT_VANILLA_BOSSES = BT_ENABLED ? BT_VANILLA_BOSSES_TUNED : {}
const BT_HEALTH_ID = $BTResourceLocation.parse('minerpg:boss_baseline_health')

// Regeneration in HP per second, always on while the boss is hurt (bosses heal out of combat
// anyway). The Harbinger's is its own config (harbinger_auto_heal); the Amethyst Crab and the
// Wither regenerate by themselves.
const BT_REGEN_TUNED = {
  'mowziesmobs:umvuthi': 7.5,
  'cataclysm:ender_guardian': 6.5,
  'minecraft:ender_dragon': 5.5,
}
const BT_REGEN = BT_ENABLED ? BT_REGEN_TUNED : {}

// Tuning off: undo what a saved boss still carries (our health modifier, Cataclysm/Mowzie config multipliers baked
// into its saved base values). Only bosses in #minerpg:tuned_boss; health keeps the same fraction.
const $BTDefaultAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.DefaultAttributes')
const $BTRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const $BTRegistryKeys = Java.loadClass('net.minecraft.core.registries.Registries')
const $BTTagKey = Java.loadClass('net.minecraft.tags.TagKey')
const $BTLiving = Java.loadClass('net.minecraft.world.entity.LivingEntity')
const BT_TUNED_TAG = $BTTagKey.create($BTRegistryKeys.ENTITY_TYPE, $BTResourceLocation.parse('minerpg:tuned_boss'))

// Entity ids in #minerpg:tuned_boss, read once the tags are loaded (KubeJS hands entity types to scripts as ids).
// var, not const: these run inside a try block on the caller's side, where Rhino rejects a const declared twice.
let btTunedIds = null
function btTuned(id) {
  if (btTunedIds == null) {
    var found = {}
    var any = false
    $BTRegistries.ENTITY_TYPE.getTagOrEmpty(BT_TUNED_TAG).forEach(holder => {
      found[String(holder.unwrapKey().get().location())] = true
      any = true
    })
    if (!any) return false
    btTunedIds = found
  }
  return btTunedIds[id] === true
}

function btUntune(entity) {
  if (!(entity instanceof $BTLiving)) return
  var id = btTypeId(entity)
  if (!btTuned(id)) return
  var type = $BTRegistries.ENTITY_TYPE.get($BTResourceLocation.parse(id))
  if (!$BTDefaultAttributes.hasSupplier(type)) return
  var defaults = $BTDefaultAttributes.getSupplier(type)
  var fraction = entity.getHealth() / entity.getMaxHealth()
  var health = entity.getAttribute($BTAttributes.MAX_HEALTH)
  if (health != null) {
    // removeModifier is overloaded (id / modifier); Rhino needs the one named.
    health['removeModifier(net.minecraft.resources.ResourceLocation)'](BT_HEALTH_ID)
    if (defaults.hasAttribute($BTAttributes.MAX_HEALTH)) health.setBaseValue(defaults.getBaseValue($BTAttributes.MAX_HEALTH))
  }
  var attack = entity.getAttribute($BTAttributes.ATTACK_DAMAGE)
  if (attack != null && defaults.hasAttribute($BTAttributes.ATTACK_DAMAGE)) {
    attack.setBaseValue(defaults.getBaseValue($BTAttributes.ATTACK_DAMAGE))
  }
  entity.setHealth(entity.getMaxHealth() * fraction)
}

function btTypeId(entity) {
  return entity == null ? null : String($BTEntityType.getKey(entity.getType()))
}

// When the boss enters the world: raise max health once (the modifier is saved with the entity,
// so a reloaded boss is not boosted twice) and keep its current health at the same fraction.
// The Wither is summoned at a third of its health and charges up; the heal hook below scales
// that charge so it still ends at full health.
// Bosses currently in a loaded world that regenerate (see BT_REGEN).
let btRegenerating = []

NativeEvents.onEvent($BTJoin, event => {
  if (event.getLevel().isClientSide()) return
  const entity = event.getEntity()
  if (!BT_ENABLED) {
    // A failure here must never stop entities from loading (it runs inside world ticking).
    try {
      btUntune(entity)
    } catch (err) {
      console.error('[minerpg] boss untune failed for ' + btTypeId(entity) + ': ' + err)
    }
    return
  }
  const id = btTypeId(entity)
  if (BT_REGEN[id] && !btRegenerating.some(e => e.entity === entity)) btRegenerating.push({ entity: entity, rate: BT_REGEN[id] })
  const tune = BT_VANILLA_BOSSES[id]
  if (!tune || tune.health == 1.0) return
  const inst = entity.getAttribute($BTAttributes.MAX_HEALTH)
  if (inst == null || inst.hasModifier(BT_HEALTH_ID)) return
  const fraction = entity.getHealth() / entity.getMaxHealth()
  inst.addPermanentModifier(new $BTModifier(BT_HEALTH_ID, tune.health - 1.0, $BTOperation.ADD_MULTIPLIED_TOTAL))
  entity.setHealth(entity.getMaxHealth() * fraction)
})

// The Wither's summon charge-up heals a fixed amount; scale it by the same health multiplier so
// the Wither still starts the fight at full health. Only while it is charging (invulnerable).
NativeEvents.onEvent($BTHeal, event => {
  const entity = event.getEntity()
  if (btTypeId(entity) != 'minecraft:wither') return
  const tune = BT_VANILLA_BOSSES['minecraft:wither']
  if (!tune) return
  if (entity.getInvulnerableTicks() > 0) event.setAmount(event.getAmount() * tune.health)
})

// Damage dealt by the boss (direct melee, or a projectile/breath cloud it owns).
NativeEvents.onEvent($BTIncomingDamage, event => {
  // KubeJS remaps DamageSource#getEntity to getActual()
  const attacker = event.getSource().getActual()
  const tune = BT_VANILLA_BOSSES[btTypeId(attacker)]
  if (!tune || tune.damage == 1.0) return
  event.setAmount(event.getAmount() * tune.damage)
})

// Once a second: heal every tracked boss; forget the ones that died or were unloaded.
let btTicks = 0
ServerEvents.tick(event => {
  btTicks++
  if (btTicks % 20 != 0) return
  if (btRegenerating.length == 0) return
  btRegenerating = btRegenerating.filter(entry => !entry.entity.isRemoved() && entry.entity.isAlive())
  btRegenerating.forEach(entry => {
    if (entry.entity.getHealth() < entry.entity.getMaxHealth()) entry.entity.heal(entry.rate)
  })
})
