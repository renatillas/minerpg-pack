// minerpg: tidy JEI. Hides items a player can never get or use in this pack.
// It runs on the server and KubeJS sends the list to every client that joins (KubeJS 7
// recipe viewer events are "common"), so one file covers singleplayer and the dedicated server.
//
// Nothing a player needs is hidden: the Orb of Origin (boss drop, race change), the Orb of
// Oblivion (talent reset), the quest book, Lootr's trophy, spawners and spawn eggs stay.
// Disabled recipes (vanilla Eye of Ender, Orb of Origin / Orb of Class, the broken LNE staff
// upgrades) are removed from the game itself, so JEI never shows them.

const JEI_HIDDEN_ITEMS = [
  // NeoOrigins classes are off (config/neoorigins/content.toml), so the class orb does nothing;
  // the four colored orbs are icon items for its own screens.
  'neoorigins:orb_of_class',
  'neoorigins:gold_orb',
  'neoorigins:pink_orb',
  'neoorigins:purple_orb',
  'neoorigins:teal_orb',
  // LNE Wizards add-on: its orbs only feed staff upgrades that need Loot & Explore, which is not
  // in the pack (those recipes are switched off in kubejs/data/lne_wizards/recipe/).
  'lne_wizards:air_magic_orb',
  'lne_wizards:arcane_magic_orb',
  'lne_wizards:earth_magic_orb',
  'lne_wizards:fire_magic_orb',
  'lne_wizards:frost_magic_orb',
  'lne_wizards:water_magic_orb',
  'lne_wizards:air_evoker_spawn_egg',
  'lne_wizards:arcane_evoker_spawn_egg',
  'lne_wizards:earth_evoker_spawn_egg',
  'lne_wizards:fire_evoker_spawn_egg',
  'lne_wizards:frost_evoker_spawn_egg',
  'lne_wizards:water_evoker_spawn_egg',
  // Quest-editor and admin blocks.
  'ftbquests:barrier',
  'ftbquests:stage_barrier',
  'ftbquests:detector',
  'ftbquests:screen_1',
  'ftbquests:screen_3',
  'ftbquests:screen_5',
  'ftbquests:screen_7',
  'ftbquests:task_screen_configurator',
  'ftbquests:loot_crate_opener',
  'ftbquests:lootcrate',
  'ftbquests:custom_icon',
  'ftbquests:missing_item',
  'ftblibrary:icon_item',
  // Lootr's own containers: Lootr swaps them in for dungeon chests by itself.
  'lootr:lootr_chest',
  'lootr:lootr_barrel',
  'lootr:lootr_trapped_chest',
  'lootr:lootr_shulker',
  'lootr:lootr_inventory',
  'lootr:decorated_pot',
  'lootr:suspicious_sand',
  'lootr:suspicious_gravel',
  // Library internals and creative-only tools.
  'moonlight:placeable_item',
  'moonlight:spawn_box',
  'champions:egg',
  'minecraft:debug_stick',
  'minecraft:command_block',
  'minecraft:chain_command_block',
  'minecraft:repeating_command_block',
  'minecraft:command_block_minecart',
  'minecraft:structure_block',
  'minecraft:structure_void',
  'minecraft:jigsaw',
  'minecraft:barrier',
  'minecraft:light',
  'minecraft:knowledge_book',
]

RecipeViewerEvents.removeEntries('item', event => {
  JEI_HIDDEN_ITEMS.forEach(id => event.remove(id))
  // Croptopia's copies of Farmer's Delight / Brewin' And Chewin' items (minerpg_croptopia.js).
  Object.keys(CROPTOPIA_KEEP).forEach(id => event.remove(id))
})
