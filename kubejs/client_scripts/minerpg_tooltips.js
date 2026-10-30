// minerpg: tooltips for the key items, boss trophies and the Arcanist's Prism.
// Rule of thumb: at most two short lines per item, saying what it does and where it comes from.
// The world tier lines match kubejs/data/apotheosis/advancement/progression/*.json.

ItemEvents.modifyTooltips(event => {
  event.add('minerpg:nether_sigil', [
    Text.gold('Use on a finished obsidian frame to open a Nether portal. Never used up.'),
    Text.gray('Raises your world tier to Ascent. Dropped by The Harbinger.'),
  ])
  event.add('minerpg:void_shard', [
    Text.lightPurple('Needed to craft Eyes of Ender. Stays in the grid.'),
    Text.gray('Raises your world tier to Summit. Dropped by Ignis.'),
  ])

  // Trophies: [boss name, world tier line or null]
  const trophies = {
    amethyst_crab: ['the Amethyst Crab', 'Raises your world tier to Venture.'],
    ancient_remnant: ['the Ancient Remnant', null],
    maledictus: ['Maledictus', null],
    leviathan: ['The Leviathan', null],
    netherite_monstrosity: ['the Netherite Monstrosity', null],
    ender_guardian: ['the Ender Guardian', 'With the Dragonscale: raises your world tier to Pinnacle.'],
    ender_dragon: ['the Ender Dragon', 'With the Citadel Keystone: raises your world tier to Pinnacle.'],
    wither: ['the Wither', null],
    ferrous_wroughtnaut: ['the Ferrous Wroughtnaut', null],
    frostmaw: ['the Frostmaw', null],
    umvuthi: ['Umvuthi, the Sunbird', null],
  }
  Object.keys(trophies).forEach(key => {
    const boss = trophies[key][0]
    const tier = trophies[key][1]
    event.add(`minerpg:trophy_${key}`, [
      Text.gray(`Proof that you stood against ${boss}. Quests ask for it.`),
      tier ? Text.yellow(tier) : Text.darkGray('Everyone nearby at the kill earns one.'),
    ])
  })

  // Apotheosis gems are all one item (apotheosis:gem) told apart by a data component, so the
  // Arcanist's Prism line is added per stack by the dynamic tooltip below.
  event.modify('apotheosis:gem', tooltip => tooltip.dynamic('minerpg_gem'))
})

ItemEvents.dynamicTooltips('minerpg_gem', event => {
  // The gem id (minerpg:caster/arcanist) is in the stack's components.
  if (String(event.item.componentString).indexOf('minerpg:caster/arcanist') < 0) return
  event.add([Text.aqua('Fits staves and wands only: adds spell power to your spells.')])
})
