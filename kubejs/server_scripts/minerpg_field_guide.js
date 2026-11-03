// minerpg: Field Guide sightings (pack 0.10.0). Every 2 seconds, for each player: if a boss is
// within 32 blocks and in line of sight, award the "seen" criterion of
// minerpg:field_guide/sighted/<key>, which opens that boss's page in the Adventurer's Handbook
// (quiet advancement toast, nothing in chat). Entering the lair, or holding the trophy, also
// opens it (criteria in the advancement itself). Advancements and pages: tools/gen_handbook.py
// (GUIDE_BOSSES); keep this list in step with it.

const $FGResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $FGEntityType = Java.loadClass('net.minecraft.world.entity.EntityType')
const $FGLiving = Java.loadClass('net.minecraft.world.entity.LivingEntity')

const FG_BOSSES = {
  'cataclysm:amethyst_crab': 'amethyst_crab',
  'mowziesmobs:ferrous_wroughtnaut': 'ferrous_wroughtnaut',
  'mowziesmobs:umvuthi': 'umvuthi',
  'mowziesmobs:frostmaw': 'frostmaw',
  'cataclysm:ancient_remnant': 'ancient_remnant',
  'cataclysm:maledictus': 'maledictus',
  'cataclysm:the_leviathan': 'leviathan',
  'cataclysm:scylla': 'scylla',
  'cataclysm:the_harbinger': 'harbinger',
  'cataclysm:netherite_monstrosity': 'netherite_monstrosity',
  'cataclysm:ignis': 'ignis',
  'cataclysm:ender_guardian': 'ender_guardian',
  'minecraft:wither': 'wither',
  'minecraft:ender_dragon': 'ender_dragon',
  'block_factorys_bosses:sandworm': 'sandworm',
  'block_factorys_bosses:yeti': 'yeti',
  'block_factorys_bosses:kraken': 'kraken',
  'block_factorys_bosses:infernal_dragon': 'infernal_dragon',
  'block_factorys_bosses:underworld_knight': 'underworld_knight',
  'graveyard:lich': 'corrupted_champion',
  'bosses_of_mass_destruction:lich': 'night_lich',
  'bosses_of_mass_destruction:gauntlet': 'gauntlet',
  'bosses_of_mass_destruction:void_blossom': 'void_blossom',
  'bosses_of_mass_destruction:obsidilith': 'obsidilith',
}
const FG_RANGE = 32

function fgAward(player, key) {
  const server = player.getServer()
  const holder = server.getAdvancements().get($FGResourceLocation.parse('minerpg:field_guide/sighted/' + key))
  if (holder == null) return
  const progress = player.getAdvancements().getOrStartProgress(holder)
  if (progress.isDone()) return
  player.getAdvancements().award(holder, 'seen')
}

let fgTicks = 0
ServerEvents.tick(event => {
  fgTicks++
  if (fgTicks % 40 != 7) return
  event.server.getPlayerList().getPlayers().forEach(player => {
    if (player.isSpectator()) return
    const box = player.getBoundingBox().inflate(FG_RANGE)
    const found = player.serverLevel().getEntitiesOfClass($FGLiving, box, e => FG_BOSSES[String($FGEntityType.getKey(e.getType()))] != null)
    found.forEach(boss => {
      if (!boss.isAlive() || !player.hasLineOfSight(boss)) return
      fgAward(player, FG_BOSSES[String($FGEntityType.getKey(boss.getType()))])
    })
  })
})
