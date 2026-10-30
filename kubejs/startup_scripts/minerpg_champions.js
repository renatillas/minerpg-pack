// minerpg: Champions filter. Champions is the pack's one elite system, but on its own it
// turns any mob into an elite (rabbits, villagers, Cataclysm bosses, the Wither, Apotheosis
// invaders...) and picks the elite tier with fixed weights, whatever the place.
// This script, run for every champion before it is created:
//   - lets only hostile mobs become champions (no animals, villagers, golems);
//   - never lets a boss (#minerpg:boss) or an Apotheosis invader/elite become one;
//   - caps the champion tier by the Dungeon Difficulty zone level at the spawn position,
//     so the strongest elites only appear in the dangerous zones.
// Champions cannot change a tier, only cancel the champion (the mob then spawns as a
// normal mob), so the cap works by cancelling champions above it. Together with the lower
// spawnChance in config/champions-server.toml this makes elites rarer overall.
// See docs/superpowers/specs/2026-10-30-minerpg-integration-plan.md (section 1).
//
// Champions 21.1.1.7 ships a KubeJS plugin class (ChampionsEvents.spawn) but no
// kubejs.plugins.txt, so KubeJS never loads it. This script listens to Champions' own
// spawn event (an Architectury event) instead. It is a startup script because that event
// can't be unregistered: the listener is registered once per game launch (startup scripts
// run once; the global flag stops a duplicate if they are reloaded by hand) and it calls
// the filter stored in global.minerpgChampionFilter, so a startup reload swaps the filter.
// The filter runs on the server only (Champions picks champions server-side).

const $Enemy = Java.loadClass('net.minecraft.world.entity.monster.Enemy')
const $TagKey = Java.loadClass('net.minecraft.tags.TagKey')
const $Registries = Java.loadClass('net.minecraft.core.registries.Registries')
const $ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $DDPatternMatching = Java.loadClass('net.dungeon_difficulty.logic.PatternMatching')
const $DDLocationData = Java.loadClass('net.dungeon_difficulty.logic.PatternMatching$LocationData')
const $ChampionEvents = Java.loadClass('top.theillusivec4.champions.api.event.ChampionEvents')
const $SpawnCallback = Java.loadClass('top.theillusivec4.champions.api.event.ChampionEvents$SpawnCallback')
const $EventResult = Java.loadClass('dev.architectury.event.EventResult')
const $EntityType = Java.loadClass('net.minecraft.world.entity.EntityType')

const BOSS_TAG = $TagKey.create($Registries.ENTITY_TYPE, $ResourceLocation.parse('minerpg:boss'))

// Set to true to log every decision (testing only; it is chatty).
const CHAMPION_DEBUG = false

// Highest champion tier (1-5) allowed at a Dungeon Difficulty zone level.
// Zone levels in config/dungeon_difficulty/difficulty_v2.json: Hearthlands 1, Wildlands 2,
// small dungeons 1-3, Frontier zone and big lairs 4-5, Nether 5-7, End 7-8.
function maxTierForZoneLevel(level) {
  if (level <= 1) return 2
  if (level <= 3) return 3
  if (level <= 5) return 4
  return 5
}

// Dungeon Difficulty's zone level at the mob's position (structure, then biome, then
// dimension), the same lookup DD uses when it scales the mob.
function zoneLevel(entity) {
  try {
    const level = entity.level()
    const difficulty = $DDPatternMatching.getDifficulty($DDLocationData.create(level, entity.blockPosition()), level)
    return difficulty == null ? 0 : difficulty.level()
  } catch (e) {
    // If DD's lookup ever fails, fall back to a middle cap instead of breaking spawns.
    return 3
  }
}

// The mob's entity type id, e.g. "minecraft:zombie". (KubeJS replaces getType() on entities
// with a string-returning version, so the type is looked up from the saved id instead.)
function entityId(entity) {
  const id = entity.getEncodeId()
  return id == null ? '' : String(id)
}

// Returns null to let the champion spawn, or the reason it is cancelled.
function championCancelReason(entity, tier) {
  if (!(entity instanceof $Enemy)) return 'not hostile'
  const type = $EntityType.byString(entityId(entity))
  // (EntityType.is(...) is overloaded, which Rhino can't pick from; read the holder's tags.)
  if (type.isPresent() && type.get().builtInRegistryHolder().tags().anyMatch(tag => tag.equals(BOSS_TAG))) return 'boss'
  // Apotheosis marks its invaders ("apoth.boss") and elites ("apoth.miniboss") in the
  // entity's persistent data when they spawn, before Champions sees them.
  const data = entity.getPersistentData()
  if (data.contains('apoth.boss') || data.contains('apoth.miniboss')) return 'apotheosis invader/elite'
  const zone = zoneLevel(entity)
  const cap = maxTierForZoneLevel(zone)
  if (tier > cap) return `tier ${tier} above cap ${cap} (zone level ${zone})`
  return null
}

global.minerpgChampionFilter = (champion, tier) => {
  const entity = champion.entity()
  const level = tier.level()
  const reason = championCancelReason(entity, level)
  if (CHAMPION_DEBUG) {
    const id = entityId(entity)
    console.info(reason == null ? `[minerpg] champion allowed: ${id} tier ${level}` : `[minerpg] champion cancelled: ${id} (${reason})`)
  }
  return reason == null
}

if (!global.minerpgChampionHooked) {
  global.minerpgChampionHooked = true
  $ChampionEvents.SPAWN.register(new $SpawnCallback({
    onSpawn: (champion, tier, ctx) => {
      try {
        return global.minerpgChampionFilter(champion, tier) ? $EventResult.pass() : $EventResult.interruptFalse()
      } catch (e) {
        // Never break a mob spawn because of the filter.
        console.error(`[minerpg] champion filter failed: ${e}`)
        return $EventResult.pass()
      }
    },
  }))
  console.info('[minerpg] Champions spawn filter registered')
}
