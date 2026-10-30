// minerpg: tooltips for the key items and boss trophies.

ItemEvents.modifyTooltips(event => {
  event.add('minerpg:nether_sigil', [
    Text.gold('Use it on a finished obsidian frame to open a Nether portal.'),
    Text.gray('Fire alone will not wake a portal in this world. Never used up.'),
    Text.darkGray('Earned by everyone who stands against The Harbinger.'),
  ])
  event.add('minerpg:void_shard', [
    Text.lightPurple('Needed to craft Eyes of Ender. Stays in the grid.'),
    Text.darkGray('Earned by everyone who stands against Ignis.'),
  ])
  const trophies = {
    amethyst_crab: 'the Amethyst Crab',
    ancient_remnant: 'the Ancient Remnant',
    maledictus: 'Maledictus',
    leviathan: 'The Leviathan',
    netherite_monstrosity: 'the Netherite Monstrosity',
    ender_guardian: 'the Ender Guardian',
    ender_dragon: 'the Ender Dragon',
    wither: 'the Wither',
    ferrous_wroughtnaut: 'the Ferrous Wroughtnaut',
    frostmaw: 'the Frostmaw',
    umvuthi: 'Umvuthi, the Sunbird',
  }
  Object.keys(trophies).forEach(key => {
    event.add(`minerpg:trophy_${key}`, [
      Text.gray(`Proof that you stood against ${trophies[key]}.`),
      Text.darkGray('Everyone nearby at the kill earns one. Keep it for the quest book.'),
    ])
  })
})
