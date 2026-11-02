// minerpg: the market (designer, 2026-11-02). One stall per job in the spawn village, selling for Gold Coins.
//
// A stall is a wandering trader that can't move, be hurt or despawn, tagged minerpg_stall and minerpg_stall_<id>.
// An op places one where they stand with /minerpg_market place <stall> (it faces where the op looks) and removes the
// nearest within 4 blocks with /minerpg_market remove. The offers are rebuilt from MARKET_STALLS every time a player
// opens a stall, so price and stock changes here reach stalls that are already placed.
// Members of the stall's job pay MARKET_DISCOUNT less (rounded down, at least 1 Gold Coin), applied to the first
// coin slot as the offer's special price, which the trade screen shows. Wandering traders have no reputation or
// Hero of the Village pricing, so everyone else pays the list price.
// Prices above 64 Gold Coins take two stacks (a trade has two cost slots), so 128 is the highest price.
// Stalls never sell job-gated items (class gear, gated shelves, strong potions, waystones and scrolls): they sell
// supplies and luxuries, and the shop is the pack's main way for coins to leave the game.
// Uses JOB_NAMES, jobOf, $MerchantOffer, $ItemCost and $Optional from minerpg_jobs.js (server scripts share one scope).

const $WanderingTrader = Java.loadClass('net.minecraft.world.entity.npc.WanderingTrader')

const MARKET_DISCOUNT = 0.25
const MARKET_MAX_PRICE = 128
const MARKET_TAG = 'minerpg_stall'

// stall id -> { job, name, offers: [[item (KubeJS item string, may carry components), count, Gold Coins]] }
const MARKET_STALLS = {
  miner: { job: 'miner', name: "Brom Deepdelve, Miner's Supplies", offers: [
    ['minecraft:torch', 32, 3], ['minecraft:iron_ingot', 16, 5], ['minecraft:gold_ingot', 8, 6],
    ['minecraft:diamond', 1, 15], ['minecraft:obsidian', 8, 15], ['minecraft:netherite_scrap', 4, 100]] },
  farmer: { job: 'farmer', name: "Willa Furrowfield, Farmer's Goods", offers: [
    ['farmersdelight:cabbage_seeds', 8, 3], ['farmersdelight:tomato_seeds', 8, 3], ['farmersdelight:rice', 8, 3],
    ['minecraft:bone_meal', 32, 4], ['minecraft:cherry_sapling', 4, 15], ['minecraft:mangrove_propagule', 4, 15],
    ['minecraft:enchanted_golden_apple', 1, 128]] },
  smith: { job: 'smith', name: "Haldor Brightanvil, Smith's Wares", offers: [
    ['minecraft:anvil', 1, 12], ['minecraft:iron_block', 4, 15],
    ['minecraft:sentry_armor_trim_smithing_template', 1, 25], ['minecraft:wild_armor_trim_smithing_template', 1, 25],
    ['minecraft:netherite_upgrade_smithing_template', 1, 80]] },
  enchanter: { job: 'enchanter', name: "Ysolde Inkwell, Enchanter's Study", offers: [
    ['minecraft:lapis_lazuli', 32, 5], ['minecraft:book', 16, 3], ['minecraft:experience_bottle', 16, 25],
    ['minecraft:enchanted_book[stored_enchantments={levels:{"minecraft:unbreaking":3}}]', 1, 40],
    ['minecraft:enchanted_book[stored_enchantments={levels:{"minecraft:mending":1}}]', 1, 100]] },
  alchemist: { job: 'alchemist', name: "Corwin Ashvial, Alchemist's Shelf", offers: [
    ['minecraft:glass_bottle', 16, 3], ['minecraft:glowstone_dust', 16, 4], ['minecraft:nether_wart', 16, 6],
    ['minecraft:blaze_rod', 4, 20], ['minecraft:ghast_tear', 1, 20],
    ['apotheosis:potion_charm[potion_contents={potion:"minecraft:regeneration"}]', 1, 90]] },
  cook: { job: 'cook', name: "Mabel Saltpan, Cook's Pantry", offers: [
    ['minecraft:sugar', 16, 3], ['farmersdelight:onion', 16, 4], ['farmersdelight:tomato', 16, 4],
    ['minecraft:golden_carrot', 8, 15], ['farmersdelight:cooking_pot', 1, 20], ['minecraft:golden_apple', 4, 70]] },
  hunter: { job: 'hunter', name: "Tamsin Ridgewatch, Hunter's Lodge", offers: [
    ['minecraft:arrow', 64, 4], ['minecraft:leather', 16, 5], ['minecraft:lead', 2, 3],
    ['minecraft:name_tag', 1, 20], ['minecraft:saddle', 1, 20], ['minecraft:totem_of_undying', 1, 128]] },
  jeweler: { job: 'jeweler', name: "Pell Glimmerstone, Jeweler's Case", offers: [
    ['jewelry:ruby', 1, 8], ['jewelry:sapphire', 1, 8], ['jewelry:topaz', 1, 8], ['jewelry:citrine', 1, 8],
    ['jewelry:jade', 1, 8], ['jewelry:tanzanite', 1, 8], ['additional_rpg_jewelry:aquamarine', 1, 8],
    ['additional_rpg_jewelry:malachite', 1, 8], ['apotheosis:gem_dust', 16, 15],
    ['apotheosis:sigil_of_withdrawal', 1, 30], ['apotheosis:sigil_of_socketing', 1, 60]] },
  explorer: { job: 'explorer', name: "Odo Farstep, Explorer's Outfitter", offers: [
    ['minecraft:map', 4, 3], ['minecraft:compass', 1, 5], ['minecraft:spyglass', 1, 8],
    ['minerpg:survey_map_settlement', 1, 10], ['minecraft:ender_pearl', 4, 15],
    ['minecraft:recovery_compass', 1, 20], ['minecraft:elytra', 1, 128]] },
}

function marketStallOf(entity) {
  if (!(entity instanceof $WanderingTrader) || !entity.getTags().contains(MARKET_TAG)) return null
  for (var id in MARKET_STALLS) {
    if (entity.getTags().contains(MARKET_TAG + '_' + id)) return id
  }
  return null
}

function marketDiscount(price) {
  return Math.max(1, Math.floor(price * MARKET_DISCOUNT))
}

// Rebuilds the stall's offers at list price, or with the job discount for a member of the stall's job.
function marketFillOffers(trader, stallId, member) {
  const stall = MARKET_STALLS[stallId]
  const gold = Item.of('coins:gold_coin').getItem()
  const offers = trader.getOffers()
  offers.clear()
  stall.offers.forEach(([id, count, price]) => {
    var costB = price > 64 ? $Optional.of(new $ItemCost(gold, price - 64)) : $Optional.empty()
    var offer = new $MerchantOffer(new $ItemCost(gold, Math.min(price, 64)), costB, Item.of(id, count),
      2147483647, 0, 0)
    if (member) offer.setSpecialPriceDiff(-marketDiscount(price))
    offers.add(offer)
  })
}

ItemEvents.entityInteracted(event => {
  var stallId = marketStallOf(event.target)
  if (stallId == null) return
  var held = String(event.player.getItemInHand(event.hand).id)
  // A name tag or lead would rename or leash the stall.
  if (held == 'minecraft:name_tag' || held == 'minecraft:lead') {
    event.cancel()
    return
  }
  // A trader serves one player at a time; leave the offers of the one trading now alone.
  if (event.target.getTradingPlayer() != null) return
  try {
    var job = MARKET_STALLS[stallId].job
    var member = jobOf(event.player, job) != null
    marketFillOffers(event.target, stallId, member)
    if (member) event.player.setStatusMessage(Text.of(`${JOB_NAMES[job]}'s discount: 25% off`).gold())
  } catch (err) {
    console.error('minerpg market: could not fill the ' + stallId + ' stall: ' + err)
  }
})

ServerEvents.commandRegistry(event => {
  const { commands: Commands, arguments: Arguments } = event
  var place = Commands.literal('place')
  Object.keys(MARKET_STALLS).forEach(id => {
    place = place.then(Commands.literal(id).executes(ctx => {
      const player = ctx.source.getPlayerOrException()
      const stall = MARKET_STALLS[id]
      const name = JSON.stringify(JSON.stringify({ text: stall.name, color: 'gold' }))
      const nbt = `{NoAI:1b,Invulnerable:1b,PersistenceRequired:1b,Silent:1b,DespawnDelay:0,CustomNameVisible:1b,` +
        `CustomName:${name},Tags:["${MARKET_TAG}","${MARKET_TAG}_${id}"],Rotation:[${player.getYRot()}f,0f]}`
      player.server.runCommandSilent(`execute in ${player.level.dimension().location()} positioned ${player.getX()} ${player.getY()} ${player.getZ()} ` +
        `run summon minecraft:wandering_trader ~ ~ ~ ${nbt}`)
      player.tell(Text.of(`Placed ${stall.name}.`).green())
      return 1
    }))
  })
  event.register(Commands.literal('minerpg_market')
    .requires(source => source.hasPermission(2))
    .then(place)
    .then(Commands.literal('remove').executes(ctx => {
      const player = ctx.source.getPlayerOrException()
      var nearest = null
      var best = 16
      player.level.getEntitiesOfClass($WanderingTrader, player.getBoundingBox().inflate(4)).forEach(e => {
        var d = e.distanceToSqr(player)
        if (marketStallOf(e) != null && d <= best) { nearest = e; best = d }
      })
      if (nearest == null) {
        player.tell(Text.of('No stall within 4 blocks.').red())
        return 0
      }
      nearest.discard()
      player.tell(Text.of('Stall removed.').green())
      return 1
    })))
})
