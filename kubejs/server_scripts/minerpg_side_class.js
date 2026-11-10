// minerpg: the Side Class tab opens once the main class tree has 9 points (pack 1.7.0).
// Design: docs/superpowers/specs/2026-11-08-minerpg-side-class-design.md. The unlock rules (side class != main class,
// 2 of 4 spells) are in startup_scripts/minerpg_side_class.js.

const $SCGateSkillsAPI = Java.loadClass('net.puffish.skillsmod.api.SkillsAPI')
const $SCGateResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')

const SC_GATE_MAIN_ID = 'skill_tree_rpgs:class_skills'
const SC_GATE_SIDE_ID = 'minerpg:side_skills'
const SC_GATE_POINTS = 9

// Opens the side tab once the main class tree has 9 points (earned, spent or not). Called at login and every 5 s.
function scUpdateGate(player) {
  var main = $SCGateSkillsAPI.getCategory($SCGateResourceLocation.parse(SC_GATE_MAIN_ID))
  var side = $SCGateSkillsAPI.getCategory($SCGateResourceLocation.parse(SC_GATE_SIDE_ID))
  if (!main.isPresent() || !side.isPresent() || side.get().isUnlocked(player)) return
  if (main.get().getPointsTotal(player) >= SC_GATE_POINTS) side.get().unlock(player)
}

// rules.json keys the main tree's roots by skill id. If a class-tree mod update (or a gen_mastery.py rerun) changes
// those ids, the "main root of your side class" rule would silently stop working; say so in the log instead.
ServerEvents.loaded(event => {
  var main = $SCGateSkillsAPI.getCategory($SCGateResourceLocation.parse(SC_GATE_MAIN_ID))
  var rules = JsonIO.read('kubejs/side_class/rules.json')
  if (!main.isPresent() || rules == null) {
    console.error('[minerpg] side class: class tree or kubejs/side_class/rules.json missing')
    return
  }
  var missing = []
  for (var id in rules.main_roots) if (!main.get().getSkill(String(id)).isPresent()) missing.push(String(rules.main_roots[id]))
  if (missing.length > 0) {
    console.error('[minerpg] side class: main tree roots not found for ' + missing.join(', ')
      + '; rerun pack/tools/gen_side_class.py')
  }
})

PlayerEvents.loggedIn(event => scUpdateGate(event.player))

var scTicks = 0
ServerEvents.tick(event => {
  scTicks++
  if (scTicks % 100 != 0) return
  event.server.getPlayerList().getPlayers().forEach(player => scUpdateGate(player))
})
