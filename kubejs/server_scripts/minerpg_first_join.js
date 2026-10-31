// minerpg: the first two minutes (pack 0.10.0). Once per player, on their very first join:
//   at once  - the Adventurer's Handbook, and ~3 minutes of protection (Resistance III +
//              Regeneration I, quiet icons, no particles);
//   after 5 s - a named map to the nearest tavern, ONE chat line, and an action-bar hint for the
//              quest book (the key name is the player's own binding);
//   after 15 s - a second action-bar hint for the handbook.
// The delays let the NeoOrigins race screen and the world-tier sync (minerpg_tier_client_sync.js,
// 40 ticks after login) settle first. Nothing here repeats: one flag per player.
//
// Players who joined before 0.10.0 already have the handbook flag and get nothing new.
//
// Cost: the tavern map is a structure search on the server thread (vanilla exploration map,
// search_radius 50, nearest match). Taverns are common in the Hearthlands, so this is about as cheap
// as the small-dungeon map (~250 ms measured in the performance study) and happens once per player.
// The time taken is logged ("first-join tavern map").

const $FJResourceKey = Java.loadClass('net.minecraft.resources.ResourceKey')
const $FJRegistries = Java.loadClass('net.minecraft.core.registries.Registries')
const $FJResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $FJLootParams = Java.loadClass('net.minecraft.world.level.storage.loot.LootParams')
const $FJLootParamsBuilder = Java.loadClass('net.minecraft.world.level.storage.loot.LootParams$Builder')
const $FJParams = Java.loadClass('net.minecraft.world.level.storage.loot.parameters.LootContextParams')
const $FJParamSets = Java.loadClass('net.minecraft.world.level.storage.loot.parameters.LootContextParamSets')
const $FJEffectInstance = Java.loadClass('net.minecraft.world.effect.MobEffectInstance')
const $FJEffects = Java.loadClass('net.minecraft.world.effect.MobEffects')
const $FJComponent = Java.loadClass('net.minecraft.network.chat.Component')
const $FJFormat = Java.loadClass('net.minecraft.ChatFormatting')

const FJ_HANDBOOK = 'patchouli:guide_book[patchouli:book="patchouli:handbook"]'
// Set by every pack version that gives the handbook on first join (0.7.0 on), so older players
// count as "already welcomed".
const FJ_FLAG = 'minerpg_handbook_given'
const FJ_PROTECTION_TICKS = 3 * 60 * 20

// Rolls one of our map loot tables at the player's position and gives the result.
function fjGiveMap(player, table) {
  const server = player.getServer()
  const key = $FJResourceKey.create($FJRegistries.LOOT_TABLE, $FJResourceLocation.parse(table))
  const lootTable = server.reloadableRegistries().getLootTable(key)
  const params = new $FJLootParamsBuilder(player.serverLevel())
    .withParameter($FJParams.ORIGIN, player.position())
    .withParameter($FJParams.THIS_ENTITY, player)
    .create($FJParamSets.CHEST)
  const started = Date.now()
  const items = lootTable.getRandomItems(params)
  const ms = Date.now() - started
  items.forEach(stack => player.give(stack))
  console.info(`[minerpg] first-join tavern map for ${player.getGameProfile().getName()}: search took ${ms} ms`)
}

function fjHint(player, keyName, before, after) {
  player.setStatusMessage($FJComponent.literal(before).withStyle($FJFormat.GRAY)
    .append($FJComponent.keybind(keyName).withStyle($FJFormat.GOLD))
    .append($FJComponent.literal(after).withStyle($FJFormat.GRAY)))
}

// A plain top-level function (server scripts share one scope), so a scratch-server probe can run
// the exact flow on a fake player.
function minerpgFirstJoin(player) {
  const data = player.persistentData
  if (data.getBoolean(FJ_FLAG)) return false
  data.putBoolean(FJ_FLAG, true)
  const server = player.getServer()
  player.give(Item.of(FJ_HANDBOOK))
  // ambient: true and no particles: a quiet icon, nothing swirling around the player.
  player.addEffect(new $FJEffectInstance($FJEffects.DAMAGE_RESISTANCE, FJ_PROTECTION_TICKS, 2, true, false, true))
  player.addEffect(new $FJEffectInstance($FJEffects.REGENERATION, FJ_PROTECTION_TICKS, 0, true, false, true))
  server.scheduleInTicks(100, () => {
    if (player.isRemoved()) return
    try {
      fjGiveMap(player, 'minerpg:map/tavern')
    } catch (err) {
      console.error('[minerpg] first-join tavern map failed: ' + err)
    }
    player.tell(Text.gold('You wake with a handbook and a map to the nearest tavern. The road is kind for a few minutes: look around.'))
    fjHint(player, 'key.ftbquests.quests', 'Your quest book: ', '')
  })
  server.scheduleInTicks(300, () => {
    if (player.isRemoved()) return
    fjHint(player, 'key.use', 'Your handbook: hold it and press ', ' to read')
  })
  return true
}

PlayerEvents.loggedIn(event => {
  minerpgFirstJoin(event.player)
})
