// minerpg: one weapon crit stat (pack 1.5.6). docs/superpowers/specs/2026-11-03-minerpg-mod-audit.md ("Crit merge")
//
// Two mods each rolled their own weapon crit: Apothic Attributes ("Crit Chance" / "Crit Damage", from Apotheosis
// affixes and gems) and Critical Strike ("Critical Hit Chance" / "Damage", from the RPG series armour, skill trees,
// Jewelry ruby gems, and its own enchantments and potions). Spell Engine also reads Critical Strike for the warrior,
// rogue and archer abilities, which then rolled a second time through Apothic Attributes.
//
// Apothic Attributes' crit is the one that counts now. Every tick, each player's Critical Strike bonus (everything
// except the mod's own innate 5% / +50%, which Apothic's base values already match) is copied onto Apothic's crit as a
// temporary modifier, and a second modifier brings Critical Strike back to exactly 0% chance and x1.0 damage, so
// neither Critical Strike nor Spell Engine's abilities roll it any more. Critical Strike's own melee and ranged crits
// are also off in config/critical_strike/server_config.json.
// Spells keep their own spell crit: spell damage can't roll Apothic's crit
// (kubejs/data/apothic_attributes/tags/damage_type/cannot_critically_strike.json).

const $CritRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const $CritResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $CritModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
const $CritOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')

// Critical Strike attributes have a base of 100: 100 = no bonus, +1% chance = +1 (or +0.01 multiplied base).
const CRIT_CS_BASE = 100.0
const CRIT_MERGE_ID = $CritResourceLocation.parse('minerpg:merged_crit')
const CRIT_CANCEL_ID = $CritResourceLocation.parse('minerpg:merged_crit_cancel')
// Critical Strike's innate modifier on every player (its 5% chance / +50% damage; Apothic's base values are the same).
const CRIT_INNATE_PATH = 'innate'

function critHolder(id) {
  return $CritRegistries.ATTRIBUTE.getHolder($CritResourceLocation.parse(id)).get()
}

var CRIT_PAIRS = null // [{ from: Critical Strike holder, to: Apothic holder }], resolved on first use

function critPairs() {
  if (CRIT_PAIRS == null) {
    CRIT_PAIRS = [
      { from: critHolder('critical_strike:chance'), to: critHolder('apothic_attributes:crit_chance') },
      { from: critHolder('critical_strike:damage'), to: critHolder('apothic_attributes:crit_damage') },
    ]
  }
  return CRIT_PAIRS
}

// The Critical Strike bonus as a fraction (0.03 = +3%), leaving out the innate modifier and our own cancel modifier.
function critBonus(inst) {
  var add = 0.0
  var base = 0.0
  var total = 1.0
  inst.getModifiers().forEach(mod => {
    var id = mod.id()
    if (id.equals(CRIT_CANCEL_ID)) return
    if (String(id.getNamespace()) == 'critical_strike' && String(id.getPath()).indexOf(CRIT_INNATE_PATH) >= 0) return
    var op = String(mod.operation().name())
    if (op == 'ADD_VALUE') add += mod.amount()
    else if (op == 'ADD_MULTIPLIED_BASE') base += mod.amount()
    else total *= 1.0 + mod.amount()
  })
  var value = (CRIT_CS_BASE + add) * (1.0 + base) * total
  return value / CRIT_CS_BASE - 1.0
}

// Sets a temporary modifier, touching the attribute only when the amount changed (each change is sent to the client).
function critSetModifier(inst, id, amount, operation) {
  var current = inst.getModifier(id)
  if (current != null && Math.abs(current.amount() - amount) < 1e-6) return
  // removeModifier is overloaded (ResourceLocation / AttributeModifier); Rhino needs the one named.
  if (current != null) inst['removeModifier(net.minecraft.resources.ResourceLocation)'](id)
  inst.addTransientModifier(new $CritModifier(id, amount, operation))
}

function critSync(player) {
  var attributes = player.getAttributes()
  critPairs().forEach(pair => {
    var from = attributes.getInstance(pair.from)
    var to = attributes.getInstance(pair.to)
    if (from == null || to == null) return
    var bonus = critBonus(from)
    critSetModifier(to, CRIT_MERGE_ID, bonus, $CritOperation.ADD_VALUE)
    // Multiply Critical Strike's final value back down to its base (0% chance, x1.0 damage).
    var current = from.getModifier(CRIT_CANCEL_ID)
    var others = from.getValue() / (current == null ? 1.0 : 1.0 + current.amount())
    if (others > 0) critSetModifier(from, CRIT_CANCEL_ID, CRIT_CS_BASE / others - 1.0, $CritOperation.ADD_MULTIPLIED_TOTAL)
  })
}

PlayerEvents.tick(event => {
  try {
    critSync(event.player)
  } catch (err) {
    if (event.player.tickCount % 200 == 0) console.error('[minerpg] crit merge failed: ' + err)
  }
})
