// minerpg: key items, boss trophies and the Nether portal rule.
// Item names live in kubejs/assets/minerpg/lang/en_us.json, tooltips in
// client_scripts/minerpg_tooltips.js, textures in kubejs/assets/minerpg/textures/item/.

StartupEvents.registry('item', event => {
  // Soft-lock key items. Neither is consumed:
  // - the sigil is used on an obsidian frame (server_scripts/minerpg_soft_locks.js);
  // - the shard stays in the crafting grid when an Eye of Ender is made (keepIngredient in
  //   server_scripts/minerpg_soft_locks.js), so one shard per player is enough for every eye.
  event.create('minerpg:nether_sigil').rarity('epic').maxStackSize(16)
  event.create('minerpg:void_shard').rarity('epic').maxStackSize(16)

  // Boss trophies: every player near a boss kill gets one. Quests check for them, so the
  // whole group is credited, not only the player who landed the last hit.
  const trophies = [
    'amethyst_crab',
    'ancient_remnant',
    'maledictus',
    'leviathan',
    'netherite_monstrosity',
    'ender_guardian',
    'ender_dragon',
    'wither',
    // Mowzie's Mobs zone bosses (optional Chapter 1 side quests, v0.4).
    'ferrous_wroughtnaut',
    'frostmaw',
    'umvuthi',
    // Pack 1.5.5 bosses (Bosses'Rise, Bosses of Mass Destruction, The Graveyard). Icons and names:
    // tools/gen_trophy_icons.py.
    'sandworm',
    'yeti',
    'kraken',
    'infernal_dragon',
    'underworld_knight',
    'corrupted_champion',
    'night_lich',
    'gauntlet',
    'void_blossom',
    'obsidilith',
  ]
  trophies.forEach(name => {
    event.create(`minerpg:trophy_${name}`).rarity('rare').maxStackSize(16)
  })

  // Explorer job: Survey Maps. Used up (right-click) into a map to the nearest place of their kind
  // (server_scripts/minerpg_jobs.js). The vanilla filled-map picture, its markings tinted per kind.
  const surveyMaps = {
    settlement: 0x3f9b3f, // villages and taverns
    crypt: 0x8a8a8a,      // small dungeons and crypts
    dungeon: 0xd4a017,    // great dungeons
    lair: 0xc0392b,       // boss lairs
  }
  Object.keys(surveyMaps).forEach(kind => {
    event.create(`minerpg:survey_map_${kind}`)
      .maxStackSize(16)
      .rarity(kind == 'lair' ? 'rare' : kind == 'dungeon' ? 'uncommon' : 'common')
      .textures({ layer0: 'minecraft:item/filled_map', layer1: 'minecraft:item/filled_map_markings' })
      .color(1, surveyMaps[kind])
  })
})

// Nether portal rule: in every dimension except the Nether, fire (flint and steel, fire
// charges, lava, lightning, dispensers...) never opens a portal. The Nether Sigil builds the
// portal blocks directly, without going through this event, so it is not affected.
// Portals made on arrival (the game building your exit portal) do not fire this event
// either, so they keep forming. Inside the Nether normal lighting is allowed, so a player
// who lost their way back can always build a portal home.
const $PortalSpawnEvent = Java.loadClass('net.neoforged.neoforge.event.level.BlockEvent$PortalSpawnEvent')

NativeEvents.onEvent($PortalSpawnEvent, event => {
  // KubeJS exposes a level's dimension id as the "dimension" property. Anything that is not
  // a real level (e.g. world generation) has none and is left alone.
  const dimension = event.getLevel().dimension
  if (dimension == null) return
  if (String(dimension) === 'minecraft:the_nether') return
  event.setCanceled(true)
})
