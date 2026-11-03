// minerpg: tooltips for the key items, boss trophies and the Arcanist's Prism.
// Rule of thumb: at most two short lines per item, saying what it does and where it comes from.
// The world tier lines match kubejs/data/apotheosis/advancement/progression/*.json.

ItemEvents.modifyTooltips(event => {
  event.add('minerpg:nether_sigil', [
    Text.gold('Touch it to a finished obsidian frame and the Nether opens. Never spent.'),
    Text.gray('Taken from The Harbinger. Your world tier rises to Ascent.'),
  ])
  // Survey Maps (Explorer job)
  const survey = {
    settlement: ['the nearest village or tavern', 'Anyone can draw one.'],
    crypt: ['the nearest crypt or small dungeon', 'Drawn by an Explorer of level 10.'],
    dungeon: ['the nearest great dungeon', 'Drawn by an Explorer of level 20.'],
    lair: ['the nearest boss lair', 'Drawn by an Explorer of level 30.'],
  }
  Object.keys(survey).forEach(kind => {
    event.add(`minerpg:survey_map_${kind}`, [
      Text.gold(`Use it to reveal a map to ${survey[kind][0]}. Copy the map for your party at a cartography table.`),
      Text.gray(survey[kind][1]),
    ])
  })
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
    sandworm: ['Sirok, the Sandworm', null],
    yeti: ['Skor, the Yeti', null],
    kraken: ['Nerakyss, the Kraken', null],
    infernal_dragon: ['Ashlord, the Infernal Dragon', null],
    underworld_knight: ['Helvar, the Underworld Knight', null],
    corrupted_champion: ['the Corrupted Champion', null],
    night_lich: ['the Night Lich', null],
    gauntlet: ['the Gauntlet', null],
    void_blossom: ['the Void Blossom', null],
    obsidilith: ['the Obsidilith', null],
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
