// minerpg: Mastery tiers in the class skill trees (designer, 2026-11-03).
// docs/superpowers/specs/2026-11-03-minerpg-mastery-tiers-design.md
//
// The class trees' skills, definitions and connections come from More RPG Classes' built-in datapack, which loads
// after KubeJS's data folder (a file there is ignored). Data generated at the `last` stage wins, so the merged trees
// that tools/gen_mastery.py writes to kubejs/mastery/ are emitted here. The new spells are plain data
// (kubejs/data/minerpg/spell/mastery_*.json).

const MASTERY_TREE = 'skill_tree_rpgs:puffish_skills/categories/class_skills/'

ServerEvents.generateData('last', event => {
  ;['skills', 'definitions', 'connections'].forEach(name => {
    var json = JsonIO.read('kubejs/mastery/class_skills/' + name + '.json')
    if (json == null) {
      console.error('[minerpg] mastery: kubejs/mastery/class_skills/' + name + '.json is missing')
      return
    }
    event.json(MASTERY_TREE + name + '.json', json)
  })
})
