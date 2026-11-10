// minerpg: tooltips for the Side Class tab's spell talents (pack 1.7.1). docs/superpowers/specs/2026-11-08-minerpg-side-class-design.md
//
// Same fix as minerpg_mastery_tooltips.js: a skill's description is {"skill_definition_id": <id>}, which the class tree
// mod looks up in a client-side list (TranslationUtil.resolvers) that it only fills for its own skills. The side tab's
// passives and upgrades reuse the main tree's ids, so they already have tooltips; its 4 spell talents per class are new
// (side_<class>_spell_<n>) and showed nothing but a name. Each gets: the tome spell's card (with the player's numbers),
// the main tree upgrade that comes with it, and the 2-of-4 rule.

const $SideTipTranslationUtil = Java.loadClass('net.skill_tree_rpgs.utils.TranslationUtil')
const $SideTipResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $SideTipSuppliers = Java.loadClass('com.google.common.base.Suppliers')
const $SideTipArrayList = Java.loadClass('java.util.ArrayList')
const $SideTipComponent = Java.loadClass('net.minecraft.network.chat.Component')
const $SideTipFormat = Java.loadClass('net.minecraft.ChatFormatting')

function sideTipLines(tome, upgrade) {
  var lines = new $SideTipArrayList($SideTipTranslationUtil.resolveSpellDetails(tome))
  var extra = $SideTipTranslationUtil.resolveSpellDetails(upgrade)
  if (extra.size() > 0) {
    lines.add($SideTipComponent.literal(''))
    lines.add($SideTipComponent.literal('Comes with:')['withStyle(net.minecraft.ChatFormatting)']($SideTipFormat.GOLD))
    lines.addAll(extra)
  }
  lines.add($SideTipComponent.literal(''))
  lines.add($SideTipComponent.literal('Side-class spell: you can learn 2 of this class\'s 4.')['withStyle(net.minecraft.ChatFormatting)']($SideTipFormat.GRAY))
  return lines
}

function sideTipRegister() {
  var defs = JsonIO.read('kubejs/data/minerpg/puffish_skills/categories/side_skills/definitions.json')
  if (defs == null) {
    console.error('[minerpg] side class tooltips: side_skills/definitions.json is missing')
    return
  }
  var ids = []
  if (defs.keySet) defs.keySet().forEach(k => ids.push(String(k)))
  else ids = Object.keys(defs)
  var count = 0
  ids.forEach(defId => {
    if (!/^side_.+_spell_[1-4]$/.test(defId)) return
    // [tome spell, main tree upgrade] (tools/gen_side_class.py)
    var spellIds = defs[defId].rewards[0].data.containers[0].spell_ids
    var tome = $SideTipResourceLocation.parse(String(spellIds[0]))
    var upgrade = $SideTipResourceLocation.parse(String(spellIds[1]))
    // Suppliers.compose: see minerpg_mastery_tooltips.js (a script function can't go into the map directly). It runs
    // on every hover, so the numbers follow the player's current spell power.
    $SideTipTranslationUtil.resolvers.put(defId, $SideTipSuppliers.compose(lines => sideTipLines(tome, upgrade), () => null))
    count++
  })
  console.info('[minerpg] side class tooltips: ' + count + ' spell talents')
}

try {
  sideTipRegister()
} catch (err) {
  console.error('[minerpg] side class tooltips failed: ' + err)
}
