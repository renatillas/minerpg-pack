// minerpg: boss baseline tuning that the mods' own configs can't do (pack 0.8.0).
// Bosses are built for a full party of four and do NOT scale with the number of players
// (ScalingMobs was removed in 0.8.0). Cataclysm and Mowzie's Mobs bosses get their health,
// damage and damage limits from their own configs (config/cataclysm-common.toml,
// config/mowziesmobs-common.toml). This script does two things those configs can't:
//   1. The Wither and the Ender Dragon (no config): more health when they appear, harder hits.
//   2. In-fight regeneration for a few bosses, so a lone, well-geared player can't simply
//      out-last them. A party of four out-damages the regeneration easily; one player can't.
// Numbers and reasoning: research_notes/Pack integration/balance_study_v2.md and
// docs/superpowers/specs/2026-10-30-minerpg-boss-balance-and-feel.md ("Boss balance implementation notes").

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
const BT_VANILLA_BOSSES = {
  'minecraft:wither': { health: 53.75, damage: 5.0 },
  'minecraft:ender_dragon': { health: 22.25, damage: 2.5 },
}
const BT_HEALTH_ID = $BTResourceLocation.parse('minerpg:boss_baseline_health')

// Regeneration in HP per second, always on while the boss is hurt (bosses heal out of combat
// anyway). The Harbinger's is its own config (harbinger_auto_heal); the Amethyst Crab and the
// Wither regenerate by themselves.
const BT_REGEN = {
  'mowziesmobs:umvuthi': 7.5,
  'cataclysm:ender_guardian': 6.5,
  'minecraft:ender_dragon': 5.5,
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
  if (entity.getInvulnerableTicks() > 0) event.setAmount(event.getAmount() * tune.health)
})

// Damage dealt by the boss (direct melee, or a projectile/breath cloud it owns).
NativeEvents.onEvent($BTIncomingDamage, event => {
  const attacker = event.getSource().getEntity()
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
