// minerpg: soft locks (Nether Sigil, Void Shard) and shared boss credit.
// See docs/superpowers/specs/2026-10-30-minerpg-progression-design.md ("Progression
// implementation notes") for the design and the edge cases.

const $PortalShape = Java.loadClass('net.minecraft.world.level.portal.PortalShape')
const $Axis = Java.loadClass('net.minecraft.core.Direction$Axis')
const $EntityType = Java.loadClass('net.minecraft.world.entity.EntityType')
const $SoundEvents = Java.loadClass('net.minecraft.sounds.SoundEvents')
const $SoundSource = Java.loadClass('net.minecraft.sounds.SoundSource')

const OVERWORLD = 'minecraft:overworld'
const NETHER = 'minecraft:the_nether'

// KubeJS exposes a level's dimension id as the "dimension" property (a ResourceLocation).
function dimensionOf(level) {
  return String(level.dimension)
}

function entityId(entity) {
  return String($EntityType.getKey(entity.getType()))
}

// ---------------------------------------------------------------------------------------
// Recipes
// ---------------------------------------------------------------------------------------
ServerEvents.recipes(event => {
  // Eyes of Ender need a Void Shard (from Ignis). The shard stays in the grid (it is not
  // used up), so one shard makes every eye a player needs.
  event.remove({ output: 'minecraft:ender_eye' })
  event.shapeless('minecraft:ender_eye', ['minecraft:ender_pearl', 'minecraft:blaze_powder', 'minerpg:void_shard'])
    .keepIngredient('minerpg:void_shard')
    .id('minerpg:ender_eye_from_void_shard')

  // Cataclysm's structure-finding eyes are crafted from an Eye of Ender. Without this they
  // would all be locked behind Ignis, including the Eye of Mech that leads to The Harbinger.
  // They take an Ender Pearl instead. The Eye of Void (End, Ender Guardian) keeps the
  // Eye of Ender: by then players have their shard.
  const locatorEyes = [
    'cataclysm:mech_eye',
    'cataclysm:cursed_eye',
    'cataclysm:desert_eye',
    'cataclysm:abyss_eye',
    'cataclysm:storm_eye',
    'cataclysm:flame_eye',
    'cataclysm:monstrous_eye',
  ]
  locatorEyes.forEach(eye => {
    event.replaceInput({ output: eye }, 'minecraft:ender_eye', 'minecraft:ender_pearl')
  })
})

// ---------------------------------------------------------------------------------------
// Nether Sigil: use it on an obsidian frame to open a portal (not consumed).
// The portal blocks are built directly with the vanilla portal shape logic, so the
// "fire never opens a portal" rule in startup_scripts/minerpg_items.js does not apply.
// ---------------------------------------------------------------------------------------
BlockEvents.rightClicked(event => {
  const item = event.getItem()
  if (item.isEmpty() || String(item.getId()) !== 'minerpg:nether_sigil') return

  const player = event.getEntity()
  const level = event.getLevel()
  const dimension = dimensionOf(level)
  // Same dimensions where vanilla allows Nether portals.
  if (dimension !== OVERWORLD && dimension !== NETHER) {
    player.setStatusMessage(Text.gray('The sigil stays dark here.'))
    event.cancel()
    return
  }

  const target = event.getBlock().getPos().relative(event.getFacing())
  const shape = $PortalShape.findEmptyPortalShape(level, target, $Axis.X)
  if (shape.isPresent()) {
    shape.get().createPortalBlocks()
    try {
      level.playSound(null, target, $SoundEvents.PORTAL_TRIGGER, $SoundSource.BLOCKS, 0.6, 1.2)
    } catch (e) {
      // The sound is only a nicety.
    }
    player.setStatusMessage(Text.gold('The frame drinks the sigil\'s heat and tears open.'))
  } else {
    player.setStatusMessage(Text.gray('Use the sigil inside a finished, empty obsidian frame.'))
  }
  // Swing the arm and stop any other interaction with the clicked block.
  player.swing(event.getHand(), true)
  event.cancel()
})

// Hint for players who try fire on obsidian outside the Nether. Fire is still placed (as in
// vanilla); the portal simply never forms.
BlockEvents.rightClicked('minecraft:obsidian', event => {
  const id = String(event.getItem().getId())
  if (id !== 'minecraft:flint_and_steel' && id !== 'minecraft:fire_charge') return
  const player = event.getEntity()
  if (dimensionOf(event.getLevel()) === NETHER) return
  player.setStatusMessage(Text.gray('The frame stays cold. Only a Nether Sigil can wake it.'))
})

// ---------------------------------------------------------------------------------------
// "Everyone nearby gets the drop": when a boss dies, every player within 64 blocks in the
// same dimension (and the killer, even if farther away) receives the boss's key item or
// trophy. Quests check for these items, so the whole group gets credit.
// ---------------------------------------------------------------------------------------
const BOSS_DROPS = {
  'cataclysm:the_harbinger': { item: 'minerpg:nether_sigil', text: 'The Harbinger falls. A Nether Sigil burns in your pack.' },
  'cataclysm:ignis': { item: 'minerpg:void_shard', text: 'Ignis gutters out. A Void Shard hums in your pack.' },
  'cataclysm:amethyst_crab': { item: 'minerpg:trophy_amethyst_crab', text: 'The Amethyst Crab is beaten. You earned a Geode Claw.' },
  'cataclysm:ancient_remnant': { item: 'minerpg:trophy_ancient_remnant', text: 'The Ancient Remnant crumbles. You earned a Sun-Bleached Fang.' },
  'cataclysm:maledictus': { item: 'minerpg:trophy_maledictus', text: 'Maledictus is broken. You earned the Frostbound Crown.' },
  'cataclysm:the_leviathan': { item: 'minerpg:trophy_leviathan', text: 'The Leviathan sinks. You earned an Abyssal Scale.' },
  'cataclysm:netherite_monstrosity': { item: 'minerpg:trophy_netherite_monstrosity', text: 'The Netherite Monstrosity cools. You earned a Molten Heart.' },
  'cataclysm:ender_guardian': { item: 'minerpg:trophy_ender_guardian', text: 'The Ender Guardian is silent. You earned the Citadel Keystone.' },
  'minecraft:ender_dragon': { item: 'minerpg:trophy_ender_dragon', text: 'The dragon is slain. You earned a Dragonscale.' },
  'minecraft:wither': { item: 'minerpg:trophy_wither', text: 'The Wither is undone. You earned an Ashen Skull Shard.' },
}
const BOSS_CREDIT_RADIUS = 64

EntityEvents.death(event => {
  const boss = event.getEntity()
  const id = entityId(boss)
  const drop = BOSS_DROPS[id]
  if (!drop) return

  const level = event.getLevel()
  const dimension = dimensionOf(level)
  // The killer always gets credit (e.g. a long bow shot from outside the radius).
  // (KubeJS exposes the damage source's attacking player as the "player" property.)
  const killer = event.getSource().player
  const killerId = killer != null ? String(killer.uuid) : null

  const candidates = []
  event.getServer().getPlayerList().getPlayers().forEach(p => candidates.push(p))
  if (killer != null && !candidates.some(p => String(p.uuid) === killerId)) candidates.push(killer)

  const recipients = candidates.filter(player => {
    const nearby = !player.isSpectator() &&
      dimensionOf(player.serverLevel()) === dimension &&
      player.distanceTo(boss) <= BOSS_CREDIT_RADIUS
    return nearby || String(player.uuid) === killerId
  })

  recipients.forEach(player => {
    player.give(Item.of(drop.item))
    player.tell(Text.gold(drop.text))
  })
  console.info(`[minerpg] ${id} died; ${drop.item} given to ${recipients.length} player(s): ` +
    recipients.map(p => p.getGameProfile().getName()).join(', '))
})
