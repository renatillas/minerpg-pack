// minerpg: RPG Coins as the pack's only money (designer, 2026-11-01).
//
// Jobs+ keeps its own coin balance and its menu can only spend that, so the balance is made a mirror of the
// coins a player carries:
//   - every COIN_SYNC_TICKS the balance is set to the value of the coins in the player's inventory, in gold
//     (Gold Coin = 1, Iron Coin = 1/9, Copper Coin = 1/81);
//   - when the balance has dropped below what was last set, the Jobs menu sold a power-up: that much is taken
//     from the inventory (all coins are taken and the rest given back as change);
//   - job level-ups pay a Gold Coin item each (Jobs+'s own coins_per_level_up is 0);
//   - job coins from before the switch are paid out once as Gold Coins.
// Coins come from quests (gen_quests.py), chest and boss loot (gen_coin_loot.py) and change hands freely.
// Known gap: coins dropped in the half second between a sync and a purchase make that purchase cheaper.
// Helpers here (coinWallet, takeCoins, giveCoins) are also used by minerpg_jobs.js (/leavejob, /minerpg_jobs).
// Uses JOB_NAMES, jobOf and $ItemStack from minerpg_jobs.js (server scripts share one scope).

const COIN_VALUE = { 'coins:gold_coin': 81, 'coins:iron_coin': 9, 'coins:copper_coin': 1 } // in Copper Coins
const COPPER_PER_GOLD = 81
const COIN_SYNC_TICKS = 10
const COIN_LAST_SET = {} // player UUID -> balance (gold) this script last set

// Value of the coins in the player's inventory (main, hotbar, offhand), in Copper Coins.
function coinWallet(player) {
  const inv = player.inventory
  let total = 0
  for (let i = 0; i < inv.getContainerSize(); i++) {
    var stack = inv.getItem(i)
    var value = COIN_VALUE[String(stack.id)]
    if (value) total += value * stack.count
  }
  return total
}

// Gives coins worth `copper` Copper Coins, in the largest coins (stacks of 64; a full inventory drops them).
function giveCoins(player, copper) {
  const gold = Math.floor(copper / 81)
  const iron = Math.floor((copper % 81) / 9)
  const counts = { 'coins:gold_coin': gold, 'coins:iron_coin': iron, 'coins:copper_coin': copper % 9 }
  Object.keys(counts).forEach(id => {
    let n = counts[id]
    while (n > 0) {
      var count = Math.min(n, 64)
      player.give(Item.of(id, count))
      n -= count
    }
  })
}

// Takes coins worth `copper` Copper Coins (or everything, if the player carries less) and gives back change.
function takeCoins(player, copper) {
  const inv = player.inventory
  const total = coinWallet(player)
  for (let i = 0; i < inv.getContainerSize(); i++) {
    if (COIN_VALUE[String(inv.getItem(i).id)]) inv.setItem(i, $ItemStack.EMPTY)
  }
  giveCoins(player, Math.max(0, total - copper))
}

// Sets the Jobs+ balance to what the player carries.
function syncCoinBalance(player) {
  const wallet = coinWallet(player) / COPPER_PER_GOLD
  if (Math.abs(player.jobsplus$getCoins() - wallet) > 0.000001) player.jobsplus$setCoins(wallet)
  COIN_LAST_SET[String(player.getGameProfile().getId())] = wallet
}

// A Gold Coin per job level gained since the last check. Levels are remembered per job in persistentData; a job
// seen for the first time (just joined) pays nothing for its starting level.
function payJobLevels(player) {
  const data = player.persistentData
  const levels = data.getCompound('minerpg_job_levels')
  let changed = false
  Object.keys(JOB_NAMES).forEach(key => {
    const job = jobOf(player, key)
    if (job == null) return
    const level = job.getLevel()
    if (!levels.contains(key) || level < levels.getInt(key)) {
      levels.putInt(key, level)
      changed = true
    } else if (level > levels.getInt(key)) {
      const gained = level - levels.getInt(key)
      giveCoins(player, gained * COPPER_PER_GOLD)
      player.tell(Text.of(`+${gained} Gold Coin${gained > 1 ? 's' : ''} (${JOB_NAMES[key]} level ${level})`).gold())
      levels.putInt(key, level)
      changed = true
    }
  })
  if (changed) data.put('minerpg_job_levels', levels)
}

PlayerEvents.tick(event => {
  const player = event.player
  if (player.tickCount % COIN_SYNC_TICKS != 0) return
  try {
    var uuid = String(player.getGameProfile().getId())
    var last = COIN_LAST_SET[uuid]
    if (last === undefined) {
      // First check this session. Job coins from before the switch become Gold Coins, once.
      if (!player.persistentData.getBoolean('minerpg_coins_migrated')) {
        var old = Math.floor(player.jobsplus$getCoins())
        if (old > 0) {
          giveCoins(player, old * COPPER_PER_GOLD)
          player.tell(Text.of(`Your ${old} job coins are now ${old} Gold Coins.`).gold())
        }
        player.persistentData.putBoolean('minerpg_coins_migrated', true)
      }
    } else {
      var spent = Math.round((last - player.jobsplus$getCoins()) * COPPER_PER_GOLD)
      if (spent > 0) takeCoins(player, spent)
    }
    payJobLevels(player)
    syncCoinBalance(player)
  } catch (e) {
    console.error(`[minerpg] coin sync failed for ${player.username}: ${e}`)
  }
})

PlayerEvents.loggedOut(event => { delete COIN_LAST_SET[String(event.player.getGameProfile().getId())] })

// Changing coins: 9 Copper <-> 1 Iron, 9 Iron <-> 1 Gold.
ServerEvents.recipes(event => {
  event.shapeless('coins:iron_coin', ['9x coins:copper_coin']).id('minerpg:coins/iron_from_copper')
  event.shapeless('9x coins:copper_coin', ['coins:iron_coin']).id('minerpg:coins/copper_from_iron')
  event.shapeless('coins:gold_coin', ['9x coins:iron_coin']).id('minerpg:coins/gold_from_iron')
  event.shapeless('9x coins:iron_coin', ['coins:gold_coin']).id('minerpg:coins/iron_from_gold')
})
