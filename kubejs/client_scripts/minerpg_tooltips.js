// minerpg: tooltips for the key items, boss trophies and the Arcanist's Prism.
// Rule of thumb: at most two short lines per item, saying what it does and where it comes from.
// The world tier lines match kubejs/data/apotheosis/advancement/progression/*.json.

ItemEvents.modifyTooltips(event => {
  event.add('minerpg:nether_sigil', [
    Text.gold('Touch it to a finished obsidian frame and the Nether opens. Never spent.'),
    Text.gray('Taken from The Harbinger. Your world tier rises to Ascent.'),
  ])
  event.add('minerpg:void_shard', [
    Text.lightPurple('No Eye of Ender without it. It stays in the grid.'),
    Text.gray('Taken from Ignis. Your world tier rises to Summit.'),
  ])

  // Trophies: [boss name, world tier line or null]
  const trophies = {
    amethyst_crab: ['the Amethyst Crab', 'Your world tier rises to Venture.'],
    ancient_remnant: ['the Ancient Remnant', null],
    maledictus: ['Maledictus', null],
    leviathan: ['The Leviathan', null],
    netherite_monstrosity: ['the Netherite Monstrosity', null],
    ender_guardian: ['the Ender Guardian', 'With the Dragonscale, your world tier rises to Pinnacle.'],
    ender_dragon: ['the Ender Dragon', 'With the Citadel Keystone, your world tier rises to Pinnacle.'],
    wither: ['the Wither', null],
    ferrous_wroughtnaut: ['the Ferrous Wroughtnaut', null],
    frostmaw: ['the Frostmaw', null],
    umvuthi: ['Umvuthi, the Sunbird', null],
  }
  Object.keys(trophies).forEach(key => {
    const boss = trophies[key][0]
    const tier = trophies[key][1]
    event.add(`minerpg:trophy_${key}`, [
      Text.gray(`Proof you stood against ${boss}. The quest book wants to see it.`),
      tier ? Text.yellow(tier) : Text.darkGray('Everyone who stood near the kill earns one.'),
    ])
  })

  // Apotheosis gems are all one item (apotheosis:gem) told apart by a data component, so the
  // Arcanist's Prism line is added per stack by the dynamic tooltip below.
  event.modify('apotheosis:gem', tooltip => tooltip.dynamic('minerpg_gem'))
})

ItemEvents.dynamicTooltips('minerpg_gem', event => {
  // The gem id (minerpg:caster/arcanist) is in the stack's components.
  if (String(event.item.componentString).indexOf('minerpg:caster/arcanist') < 0) return
  event.add([Text.aqua('Staves and wands only. Your spells hit harder.')])
})
