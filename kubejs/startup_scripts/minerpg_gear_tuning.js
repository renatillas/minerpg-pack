// minerpg: attack damage of weapons that hit too hard for where they drop (pack 1.5.2, designer: Bosses'Rise gear
// "less powerful and using the apotheosis system"). Runs on both sides, so tooltips show the tuned numbers.
// Values are the weapon's own attack damage modifier (the tooltip adds 1 for the bare hand). Boss drops also always
// roll an Apotheosis rarity (kubejs/data/apotheosis/loot_modifiers/affix_conversion.json), which adds back power.
//   Helvar's Sword (Chapter 2 boss): 13 -> 10, just under the netherite claymore (11.5).
//   Pirate Saber, Large Sword (minions and chests): 11 -> 7, the iron/diamond class tier.
//   Kraken Trident (crafted from the late Chapter 1 Kraken's teeth): 9 -> 8.

const $GTItemAttributeEvent = Java.loadClass('net.neoforged.neoforge.event.ItemAttributeModifierEvent')
const $GTAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const $GTModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
const $GTItems = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')

const GT_ATTACK_DAMAGE = {
  'block_factorys_bosses:knight_sword': 10,
  'block_factorys_bosses:pirate_saber': 7,
  'block_factorys_bosses:large_sword': 7,
  'block_factorys_bosses:kraken_trident': 8,
}

NativeEvents.onEvent($GTItemAttributeEvent, event => {
  var target = GT_ATTACK_DAMAGE[String($GTItems.ITEM.getKey(event.getItemStack().getItem()))]
  if (target == null) return
  // Copy first: replacing while walking the live list would change it under the loop.
  var damage = []
  event.getModifiers().forEach(entry => { if (entry.attribute().is($GTAttributes.ATTACK_DAMAGE)) damage.push(entry) })
  damage.forEach(entry => {
    var old = entry.modifier()
    event.replaceModifier(entry.attribute(), new $GTModifier(old.id(), target, old.operation()), entry.slot())
  })
})
