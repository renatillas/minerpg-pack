// minerpg: tooltips for the Mastery skills (pack 1.5.2). docs/superpowers/specs/2026-11-03-minerpg-mastery-tiers-design.md
//
// A Skill Tree RPGs skill's description is {"skill_definition_id": <id>}: the mod looks the id up in a client-side
// list (TranslationUtil.resolvers) that it only fills for its own skills, so the Mastery skills showed no tooltip.
// This adds every Mastery skill that grants a spell to that list, with the same tooltip the mod's own spell skills
// get (the spell's description with its numbers). Stat skills use a plain translated description instead
// (tools/gen_mastery.py).

const $MasteryTranslationUtil = Java.loadClass('net.skill_tree_rpgs.utils.TranslationUtil')
const $MasteryResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
// The list holds java.util.function.Supplier values behind a raw Map.put, so a script function would go in
// unconverted (checked on the scratch server). Guava's Suppliers.compose takes typed suppliers, so Rhino converts
// the function there; it reruns on every hover, so the numbers follow the player's current spell power.
const $MasterySuppliers = Java.loadClass('com.google.common.base.Suppliers')

function masteryRegisterTooltips() {
  var defs = JsonIO.read('kubejs/mastery/class_skills/definitions.json')
  if (defs == null) {
    console.error('[minerpg] mastery tooltips: kubejs/mastery/class_skills/definitions.json is missing')
    return
  }
  var count = 0
  // JsonIO hands back a Java map (keySet) or a plain object (Object.keys), depending on the KubeJS build.
  var ids = []
  if (defs.keySet) defs.keySet().forEach(k => ids.push(String(k)))
  else ids = Object.keys(defs)
  ids.forEach(defId => {
    var rewards = defs[defId].rewards || []
    rewards.forEach(reward => {
      if (String(reward.type) != 'skill_tree_rpgs:spell') return
      reward.data.containers.forEach(container => {
        container.spell_ids.forEach(spellId => {
          if (String(spellId).indexOf('minerpg:') != 0) return
          var id = $MasteryResourceLocation.parse(String(spellId))
          $MasteryTranslationUtil.resolvers.put(String(defId),
            $MasterySuppliers.compose(lines => lines, () => $MasteryTranslationUtil.resolveSpellDetails(id)))
          count++
        })
      })
    })
  })
  console.info('[minerpg] mastery tooltips: ' + count + ' spell skills')
}

try {
  masteryRegisterTooltips()
} catch (err) {
  console.error('[minerpg] mastery tooltips failed: ' + err)
}
