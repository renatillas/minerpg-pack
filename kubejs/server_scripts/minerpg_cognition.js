// minerpg: Cognition kept to its Experience Obelisk (designer, 2026-11-03: "do the obelisk and remove the items we
// don't care about"). The obelisk is the party's shared XP store: anyone can put levels in or take them out at it.
// Kept: the obelisk and what it is made of (Cognitive Flux, from overworld items here -> smelted Amalgam -> Alloy and Crystal -> Astute
// Assembly). Everything else (Cognitive gear and tools, amulets, flasks, bookshelves, machines, agars, Forgotten Dust)
// loses its recipes and leaves the recipe viewer (minerpg_recipe_viewer.js), so nobody can get it. Forgotten Dust's
// chest loot is off too (kubejs/data/cognition/loot_modifiers/); Flux in ruined portals and Assemblies in desert
// pyramids stay, as a head start on the obelisk.

const COGNITION_REMOVED = [
  'accelerator', 'archivers_bookshelf', 'attunement_staff', 'bibliophage', 'calcarine_matrix', 'cognitium_bucket',
  'cognitive_alloy_block', 'cognitive_axe', 'cognitive_boots', 'cognitive_bow', 'cognitive_chestplate',
  'cognitive_crystal_block', 'cognitive_helmet', 'cognitive_hoe', 'cognitive_leggings', 'cognitive_pickaxe',
  'cognitive_rod', 'cognitive_shears', 'cognitive_shovel', 'cognitive_sword', 'daydream_bottle',
  'enchanted_bookshelf', 'enlightened_amulet', 'experience_fountain', 'extravagant_agar', 'flask_of_chaos',
  'flask_of_hades', 'flask_of_poseidon', 'flint_and_cognitive_alloy', 'fluorescent_agar', 'fluorescent_jelly',
  'forgotten_dust', 'forgotten_dust_block', 'fortuitous_amulet', 'infected_archivers_bookshelf',
  'infected_bookshelf', 'infected_enchanted_bookshelf', 'insightful_agar', 'linear_accelerator', 'memory_tablet',
  'mending_neurogel', 'mending_neurogel_blob', 'molecular_metamorpher', 'nightmare_bottle', 'nutrient_agar',
  'precision_dispeller', 'primordial_assembly', 'transforming_focus', 'whisperglass'
].map(id => 'cognition:' + id)

ServerEvents.recipes(event => {
  COGNITION_REMOVED.forEach(id => event.remove({ output: id }))
  // Flux without Nether items (designer, pack 1.5.2: the obelisk before the Nether). Cognition's own recipe takes
  // quartz and soul sand; this one takes lapis, an amethyst shard and paper, so a party can build the obelisk in
  // Chapter 1. Every later step (Amalgam, Alloy, Crystal, Astute Assembly) already uses overworld items.
  event.remove({ id: 'cognition:cognitive_flux' })
  event.shapeless('4x cognition:cognitive_flux', ['minecraft:lapis_lazuli', 'minecraft:amethyst_shard', 'minecraft:paper'])
    .id('minerpg:cognition/cognitive_flux')
})
