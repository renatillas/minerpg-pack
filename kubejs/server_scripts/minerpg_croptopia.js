// minerpg: Croptopia joined to the pack's food (designer, 2026-11-03: "integrate Croptopia to what we have").
// docs/superpowers/specs/2026-11-03-minerpg-mod-audit.md
//
// Croptopia has its own copy of 19 crops and dishes Farmer's Delight or Brewin' And Chewin' already have. The pack keeps
// one of each: Croptopia's copy loses its recipes and leaves the recipe viewer (minerpg_recipe_viewer.js), recipes that
// use it take the kept item, and a copy someone still has turns into the kept one at the crafting table, one for one.
// Its wild tomato, cabbage, onion and rice don't generate (kubejs/data/croptopia/neoforge/biome_modifier/, replaced with "none").
// The Cook tiers for Croptopia's other dishes are job data (tools/gen_jobs.py, CROPTOPIA_DUPLICATES lists the same
// 19 names); its "Cooking Pot" tool is called "Stock Pot" (kubejs/assets/croptopia/lang) so it isn't mixed up with
// Farmer's Delight's Cooking Pot.

// Croptopia item -> the item the pack keeps.
const CROPTOPIA_KEEP = {
  'croptopia:tomato': 'farmersdelight:tomato',
  'croptopia:cabbage': 'farmersdelight:cabbage',
  'croptopia:onion': 'farmersdelight:onion',
  'croptopia:rice': 'farmersdelight:rice',
  'croptopia:tomato_seed': 'farmersdelight:tomato_seeds',
  'croptopia:cabbage_seed': 'farmersdelight:cabbage_seeds',
  'croptopia:onion_seed': 'farmersdelight:onion',
  'croptopia:rice_seed': 'farmersdelight:rice',
  'croptopia:bacon': 'farmersdelight:bacon',
  'croptopia:cooked_bacon': 'farmersdelight:cooked_bacon',
  'croptopia:milk_bottle': 'farmersdelight:milk_bottle',
  'croptopia:melon_juice': 'farmersdelight:melon_juice',
  'croptopia:apple_pie': 'farmersdelight:apple_pie',
  'croptopia:fruit_salad': 'farmersdelight:fruit_salad',
  'croptopia:hamburger': 'farmersdelight:hamburger',
  'croptopia:beef_stew': 'farmersdelight:beef_stew',
  'croptopia:pumpkin_soup': 'farmersdelight:pumpkin_soup',
  'croptopia:ratatouille': 'farmersdelight:ratatouille',
  'croptopia:shepherds_pie': 'farmersdelight:shepherds_pie',
  'croptopia:beer': 'brewinandchewin:beer',
  'croptopia:mead': 'brewinandchewin:mead',
  'croptopia:pizza': 'brewinandchewin:pizza',
  'croptopia:quiche': 'brewinandchewin:quiche',
}

ServerEvents.recipes(event => {
  Object.keys(CROPTOPIA_KEEP).forEach(id => {
    var kept = CROPTOPIA_KEEP[id]
    event.remove({ output: id })
    event.replaceInput({}, id, kept)
    event.shapeless(kept, [id]).id('minerpg:croptopia/' + id.split(':')[1] + '_to_kept')
  })
})

// Seeds aren't the vegetable (pack 1.5.7). Croptopia lists each seed in its crop's tag (c:lettuce holds lettuce seeds),
// so a cheap market seed went into salads, wraps and pizza in place of the crop. The tags below are every c:<crop> tag
// that holds both the crop and its Croptopia seed (checked in the jars). Croptopia's seed-only tags (c:tomato, c:onion
// and others, whose crop tag is the plural) and the seed, chicken food and season tags keep their seeds.
const CROPTOPIA_CROP_TAGS = ['asparagus', 'barley', 'basil', 'broccoli', 'cabbage', 'cauliflower', 'celery',
  'coffee_beans', 'corn', 'garlic', 'honeydew', 'hops', 'kale', 'leek', 'lettuce', 'mustard', 'oat', 'pepper',
  'rhubarb', 'rice', 'spinach', 'tea_leaves', 'turmeric', 'vanilla', 'zucchini']

ServerEvents.tags('item', event => {
  CROPTOPIA_CROP_TAGS.forEach(crop => {
    // Croptopia adds the seed both by id and through its seed tag (#c:seeds/<crop>, which also holds Farmer's
    // Delight's cabbage seeds), so both go.
    event.remove('c:' + crop, /^croptopia:.*_seeds?$/)
    event.remove('c:' + crop, '#c:seeds/' + crop)
  })
})
