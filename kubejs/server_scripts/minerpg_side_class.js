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

PlayerEvents.loggedIn(event => scUpdateGate(event.player))

var scTicks = 0
ServerEvents.tick(event => {
  scTicks++
  if (scTicks % 100 != 0) return
  event.server.getPlayerList().getPlayers().forEach(player => scUpdateGate(player))
})
