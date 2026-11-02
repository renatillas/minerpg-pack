// minerpg: keep the client's view of the Apotheosis world tier tutorial in step with the server.
//
// Our tiers are set by the server (function minerpg:tier/sync -> /apoth set_world_tier), which
// awards Apotheosis' "world tiers activated" stat on the server only. Vanilla never pushes stats
// to the client unless the Statistics screen asks, so the client keeps thinking the tutorial is
// active: affixed gear shows "This item has an unknown power" and the Ctrl+T screen opens the
// tutorial. Finishing or skipping that tutorial sends a tier-change packet, and with manual tier
// changes disabled the server answers by disconnecting the player.
//
// Fix: make sure every player has a tier (runs the sync function on join), then send their stats
// to the client on join and whenever their tier changes, so the tutorial never shows.

const $TCWorldTier = Java.loadClass('dev.shadowsoffire.apotheosis.tiers.WorldTier')

const tcLastTier = {}

function tcSendStats(player) {
  try {
    // (Through the player list: KubeJS replaces player.getStats() with its own wrapper, which can't send.)
    player.server.getPlayerList().getPlayerStats(player).sendStats(player)
  } catch (err) {
    console.error('minerpg tier sync: could not send stats to ' + player.username + ': ' + err)
  }
}

PlayerEvents.loggedIn(event => {
  const player = event.player
  const server = event.server
  server.scheduleInTicks(40, () => {
    if (player.isRemoved()) return
    server.runCommandSilent('execute as ' + player.username + ' run function minerpg:tier/sync')
    tcLastTier[player.username] = String($TCWorldTier.getTier(player))
    tcSendStats(player)
  })
})

PlayerEvents.loggedOut(event => {
  delete tcLastTier[event.player.username]
})

// Tier changes come from advancement rewards (boss items); check every 2 s and resend stats once.
let tcTicks = 0
ServerEvents.tick(event => {
  tcTicks++
  if (tcTicks % 40 != 0) return
  event.server.players.forEach(player => {
    const name = player.username
    if (!(name in tcLastTier)) return
    const tier = String($TCWorldTier.getTier(player))
    if (tier != tcLastTier[name]) {
      tcLastTier[name] = tier
      tcSendStats(player)
    }
  })
})
