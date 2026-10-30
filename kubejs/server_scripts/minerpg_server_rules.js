// minerpg: server rules for a small group, and the Adventurer's Handbook.
// See docs/server-setup.md and docs/superpowers/specs/2026-10-30-minerpg-polish-plan.md
// ("Implementation notes") for the reasoning.

// ---------------------------------------------------------------------------------------
// Game rules. Set once per world, the first time the server loads it (new worlds, and an
// existing world the first time it runs pack 0.7.0). A flag in the server's saved KubeJS data
// remembers that, so an admin can change any of these later with /gamerule and it sticks.
// The same three /gamerule commands are listed in docs/server-setup.md.
//
// mobGriefing is NOT turned off: it would also stop villagers farming, sheep eating grass,
// snow golems, foxes and more. Creeper/ghast/Wither block damage and enderman block pickup are
// switched off one by one below instead.
// keepInventory stays false on purpose: Hardcore Revival's downed state is the safety net.
// ---------------------------------------------------------------------------------------
const RULES_FLAG = 'minerpg_rules_v1'
const GAME_RULES = {
  playersSleepingPercentage: '25', // 1 of 4 players in bed skips the night
  doInsomnia: 'false', // no phantoms
  keepInventory: 'false',
}

ServerEvents.loaded(event => {
  const server = event.server
  const data = server.persistentData
  if (data.getBoolean(RULES_FLAG)) return
  Object.keys(GAME_RULES).forEach(rule => {
    server.runCommandSilent(`gamerule ${rule} ${GAME_RULES[rule]}`)
  })
  data.putBoolean(RULES_FLAG, true)
  console.info(`[minerpg] game rules set for this world: ${JSON.stringify(GAME_RULES)}`)
})

// ---------------------------------------------------------------------------------------
// No block damage from creepers, ghast fireballs, wither skulls or the Wither's spawn blast. The
// explosion still happens and still hurts and knocks back entities; only the list of blocks
// it would break (and set on fire) is emptied. TNT, beds, respawn anchors, end crystals and
// mod bosses are untouched.
// Endermen: kubejs/data/minecraft/tags/block/enderman_holdable.json is empty, so they never
// pick blocks up.
// ---------------------------------------------------------------------------------------
const $Detonate = Java.loadClass('net.neoforged.neoforge.event.level.ExplosionEvent$Detonate')
const $EntityTypeForRules = Java.loadClass('net.minecraft.world.entity.EntityType')
const NO_BLOCK_DAMAGE = {
  'minecraft:creeper': true,
  'minecraft:fireball': true, // ghast fireball (also when a player bats it back)
  'minecraft:wither_skull': true,
  'minecraft:wither': true, // its spawn blast only; blocks it smashes when hurt are not an explosion
}

NativeEvents.onEvent($Detonate, event => {
  const source = event.getExplosion().getDirectSourceEntity()
  if (source == null) return
  const id = String($EntityTypeForRules.getKey(source.getType()))
  if (NO_BLOCK_DAMAGE[id]) event.getAffectedBlocks().clear()
})

// ---------------------------------------------------------------------------------------
// Adventurer's Handbook (Patchouli book patchouli:handbook, written by tools/gen_handbook.py
// into patchouli_books/handbook/). Given once on a player's first join; the welcome quest
// gives one too, and a book + a feather crafts another.
// ---------------------------------------------------------------------------------------
const HANDBOOK = 'patchouli:guide_book[patchouli:book="patchouli:handbook"]'
const HANDBOOK_FLAG = 'minerpg_handbook_given'

PlayerEvents.loggedIn(event => {
  const player = event.player
  if (player.persistentData.getBoolean(HANDBOOK_FLAG)) return
  player.persistentData.putBoolean(HANDBOOK_FLAG, true)
  player.give(Item.of(HANDBOOK))
  player.tell(Text.gold('You carry an Adventurer\'s Handbook. Right-click it any time you wonder how something works.'))
})

ServerEvents.recipes(event => {
  event.shapeless(Item.of(HANDBOOK), ['minecraft:book', 'minecraft:feather']).id('minerpg:handbook')
})
