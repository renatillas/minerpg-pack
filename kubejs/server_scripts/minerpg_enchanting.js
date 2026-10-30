// minerpg: enchanting tweaks.
// Spell Infinity (spells stop using runes) is a reward, not something you roll early at an
// enchanting table: Spell Engine puts it in #minecraft:non_treasure, which also feeds the
// enchanting table, random loot books and librarian trades. Taking it out of that tag removes
// it from all three. The quest book hands out one Spell Infinity book for defeating Ignis
// (tools/gen_quests.py, quest "Ignis").
// See docs/superpowers/specs/2026-10-30-minerpg-integration-plan.md (section 3).

ServerEvents.tags('enchantment', event => {
  // Not added to #minecraft:treasure either, so Apothic Enchanting's treasure shelves can't
  // roll it.
  event.remove('minecraft:non_treasure', 'spell_engine:spell_infinity')
})
