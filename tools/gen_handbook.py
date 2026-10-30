#!/usr/bin/env python3
"""Generate the Adventurer's Handbook (Patchouli book) for the minerpg pack.

Run from anywhere:  python3 pack/tools/gen_handbook.py
Writes (wiping the folder first):
  pack/patchouli_books/handbook/book.json
  pack/patchouli_books/handbook/en_us/categories/*.json
  pack/patchouli_books/handbook/en_us/entries/<category>/*.json

Why this location: Patchouli 1.21.1-93 only finds book.json inside mod jars
(data/<modid>/patchouli_books) or in the game folder's patchouli_books/ ("external" books).
KubeJS data/assets folders are a datapack/resource pack, not a mod, so a book there is never
registered. An external book's id is patchouli:<folder name> (here patchouli:handbook) and its
pages are read from the same folder. packwiz installs pack/patchouli_books/ into the game
folder on both client and server.

Text: original, short pages. Patchouli formatting: $(br) line break, $(br2) blank line,
$(li) bullet, $(l)bold$(), $(o)italic$(), $(item)highlight$(), $(k:<key id>) shows the
player's current key for that binding (so the book stays right after rebinding).
The book uses text_overflow_mode "resize": a page that runs long shrinks instead of clipping.
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack
BOOK = os.path.join(ROOT, 'patchouli_books', 'handbook')
NS = 'patchouli'  # external books always live in the patchouli namespace

# The give/recipe/quest code refers to this item; keep in sync with
# kubejs/server_scripts/minerpg_server_rules.js and tools/gen_quests.py.
BOOK_ID = f'{NS}:handbook'


def text(t, title=None):
    p = {'type': 'patchouli:text', 'text': t}
    if title:
        p['title'] = title
    return p


def spotlight(item, t, title=None):
    p = {'type': 'patchouli:spotlight', 'item': item, 'text': t}
    if title:
        p['title'] = title
    return p


def crafting(recipe, t=None):
    p = {'type': 'patchouli:crafting', 'recipe': recipe}
    if t:
        p['text'] = t
    return p


def k(binding):
    return f'$(k:{binding})'


# --------------------------------------------------------------------------------------
# Categories: (id, name, description, icon)
# --------------------------------------------------------------------------------------
CATEGORIES = [
    ('getting_started', 'Getting Started', 'What this world is about and how to begin.', 'minecraft:compass'),
    ('races', 'Races', 'The eight folk you can be born as.', 'neoorigins:orb_of_origin'),
    ('classes', 'Classes', 'Tomes, weapons, spells and talents.', 'wizards:wand_arcane'),
    ('professions', 'Professions', 'Jobs, what they make and how they level.', 'minecraft:smithing_table'),
    ('world', 'World & Danger', 'Zones, dungeon levels, world tiers and elites.', 'minecraft:zombie_head'),
    ('bosses', 'Bosses & Chapters', 'The road through three chapters and the keys that open it.', 'minerpg:nether_sigil'),
    ('loot', 'Loot', 'Rarity, affixes, sockets, gems and reforging.', 'minecraft:diamond_sword'),
    ('party', 'Party', 'Playing together: the Party HUD, shared talents, reviving.', 'minecraft:shield'),
    ('keys', 'Keys', 'Every key the pack uses, as you have it bound right now.', 'minecraft:tripwire_hook'),
]

# --------------------------------------------------------------------------------------
# Entries: category -> [(id, name, icon, pages)]
# --------------------------------------------------------------------------------------
E = {}

E['getting_started'] = [
    ('welcome', 'Welcome, Traveler', 'minecraft:compass', [
        text('This is a world for a small group of friends. Pick a folk, pick a calling, learn a trade, '
             'and push from the Overworld into the Nether and finally the End.$(br2)'
             f'The quest book ({k("key.ftbquests.quests")}) tells you what to try next and pays you for it. '
             'This handbook explains how things work.'),
        crafting('minerpg:handbook', 'Lost your handbook? A book and a feather make a new one.'),
    ]),
    ('first_hour', 'Your First Hour', 'minecraft:clock', [
        text('$(li)Choose your folk when you first join (see Races).'
             f'$(li)Open the quest book ({k("key.ftbquests.quests")}) and claim $(item)Choose Your Calling$() for your class kit.'
             '$(li)Put the tome in its spell book slot, hold the weapon and cast.'
             f'$(li)Join two jobs ({k("key.jobsplus.open_menu")}).'
             f'$(li)Form a party ({k("key.partyhud.open_screen")}).'),
        text('You start in a plains village. Its $(item)gazebo$() holds a Spell Binding Table, its class '
             'buildings sell gear for your calling, and a waystone there lets you come back from anywhere.$(br2)'
             'Then head out: the Hearthlands around you are the gentlest land in the world.'),
    ]),
    ('house_rules', 'House Rules', 'minecraft:red_bed', [
        text('A few rules make life easier for a small group:'
             '$(li)One sleeper is enough to skip the night.'
             '$(li)No phantoms.'
             '$(li)Creepers, ghast fireballs and wither skulls do not break blocks. Endermen do not pick blocks up.'
             '$(li)Villagers still farm, sheep still eat grass.'),
        text('$(li)You drop your things when you die. If friends are online you fall $(item)downed$() first, '
             'and they can pick you up (see Party).'
             '$(li)Dungeon chests are personal: everyone finds their own loot in the same chest.'
             '$(li)Mining is blocked inside many surface dungeons (see World & Danger).'),
    ]),
]

RACES = [
    ('hearthfolk', 'Hearthfolk', 'minecraft:bread', 'Village people, at home anywhere with a hearth.',
     ['One extra combat roll charge.', 'Villagers give you better prices.'],
     'Rally (2 min): you and players within 8 blocks gain Speed and Resistance for 10 seconds.',
     'None.'),
    ('deepkin', 'Deepkin', 'minecraft:deepslate', 'Stout folk of the deepslate.',
     ['+2 armor and faster mining.', 'Night vision whenever the sky is out of sight.', 'A little Earth spell power.'],
     'Stoneskin (90 s): strong Resistance for 10 seconds; cures poison.',
     'A bit smaller, and slow swimmers.'),
    ('grovekin', 'Grovekin', 'minecraft:azalea', 'Elves of the lush forests.',
     ['More ranged damage.', 'A little Nature and Healing power.', 'Faster in forests.'],
     'Entangle (90 s): creatures within 6 blocks are rooted for 4 seconds.',
     'One heart less.'),
    ('tuskborn', 'Tuskborn', 'minecraft:gold_ingot', 'Tusked folk of the bastions.',
     ['More critical damage.', 'Harder to knock back.', 'Piglins leave you alone (brutes do not).'],
     'Battle Fury (2 min): swing and dig much faster for 15 seconds.',
     'Villagers charge you more.'),
    ('emberkin', 'Emberkin', 'minecraft:blaze_powder', 'Blaze-touched and fire-proof.',
     ['Immune to fire and lava.', 'Fire spell power.'],
     'Ember Burst (90 s): burns and pushes back creatures within 5 blocks.',
     'Water and rain hurt you.'),
    ('rimeborn', 'Rimeborn', 'minecraft:packed_ice', 'Kin of the ice spikes.',
     ['Immune to freezing; walk through powder snow at full speed.', 'Frost spell power.'],
     'Frost Nova (90 s): slows every creature within 7 blocks for 6 seconds.',
     'Weakened in the Nether.'),
    ('voidborn', 'Voidborn', 'minecraft:ender_pearl', 'Enderman-kin from the End.',
     ['Arcane spell power.', 'Endermen do not mind your gaze.'],
     'Blink (1 min): teleport to the block you look at, up to 10 blocks away.',
     'Water hurts you (rain does not).'),
    ('gravebound', 'Gravebound', 'minecraft:soul_sand', 'Undead of the soul sand valleys.',
     ['Soul and Shadow spell power.', 'Monsters notice you later.'],
     'Soul Siphon (90 s): drain 6 health from the creature in your sights.',
     'All healing you receive is a little weaker.'),
]


def race_entry(rid, name, icon, blurb, perks, power, drawback):
    t = (f'$(o){blurb}$()$(br2)$(l)Gifts$()' + ''.join(f'$(li){p}' for p in perks)
         + f'$(br2)$(l)Power$() ({k("key.neoorigins.skill_1")})$(br){power}'
         + f'$(br2)$(l)Drawback$()$(br){drawback}')
    return (rid, name, icon, [text(t)])


E['races'] = [
    ('folk', 'Choosing a Folk', 'neoorigins:orb_of_origin', [
        text('You pick your folk the first time you join. Each folk has two or three small gifts, one '
             f'racial power on {k("key.neoorigins.skill_1")} with a long cooldown, and one light drawback.$(br2)'
             'The gifts are small next to your class and gear, and every class works with every folk. '
             'Pick the one you like.'),
        text(f'Press {k("key.neoorigins.view_info")} to read your folk\'s powers in game.'),
    ]),
] + [race_entry(*r) for r in RACES] + [
    ('change', 'Changing Your Folk', 'neoorigins:orb_of_origin', [
        spotlight('neoorigins:orb_of_origin',
                  'An $(item)Orb of Origin$() lets you choose again. It cannot be crafted: The Harbinger, '
                  'Ignis and the Ender Guardian drop one.$(br2)Your first change is free; each later change '
                  'costs 10 experience levels for every change before it.'),
    ]),
]

E['classes'] = [
    ('how', 'How Classes Work', 'spell_engine:spell_book', [
        text('Your class is the $(item)tome$() you carry and the $(item)weapon$() you hold.$(br2)'
             'Put the tome in the spell book slot of your inventory and hold a weapon of the same class. '
             'The weapon\'s own spell works right away. Everything else comes from binding new spells into '
             'the tome.'),
        text('Your first kit comes from the quest $(item)Choose Your Calling$(): tome, starter weapon, one '
             'armor piece, and runes or arrows.$(br2)You can learn a second class later by making its tome '
             'at a Spell Binding Table. Talents follow one class tree at a time.'),
    ]),
    ('casting', 'Casting', 'runes:arcane_stone', [
        text('Right-click casts your weapon\'s first spell. While you hold a spell weapon, the hotbar keys '
             'cast the spells shown on the spell bar above it. Hold '
             f'{k("keybindings.spell_engine.bypass_spell_hotbar")} to use your normal hotbar instead.'),
        text('Many spells burn $(item)runes$(). Make them at a $(item)Rune Crafting Altar$(): it gives more '
             'runes for the same materials than a crafting table.$(br2)Defeating Ignis earns a book of '
             '$(item)Spell Infinity$(): on your weapon, spells stop using runes.'),
    ]),
    ('binding', 'Spell Binding Table', 'spell_engine:spell_binding', [
        text('Every plains village has a gazebo with a Spell Binding Table. You can also build one and ring it '
             'with bookshelves.$(br2)Put your tome in and bind a new spell with experience levels. Stronger '
             'spells ask for more levels, so they open up as you grow.'),
    ]),
    ('talents', 'Talents', 'skill_tree_rpgs:orb_of_oblivion', [
        text(f'Press {k("key.puffish_skills.open")} for your talent trees. Kills earn talent experience, '
             'shared with party members within 200 blocks.$(br2)Kills fill the class tree up to 9 points. '
             'Four more come from the great bosses: The Harbinger, the Netherite Monstrosity, Ignis and the '
             'Ender Guardian.'),
        text('Changed your mind? An $(item)Orb of Oblivion$() resets your talents so you can spend them '
             'again, or on another class tree.'),
    ]),
    ('callings', 'The Callings', 'minecraft:book', [
        text('$(li)$(l)Wizards$(): Arcane, Fire, Frost.'
             '$(li)$(l)Elemental mages$(): Water, Earth, Wind.'
             '$(li)$(l)Paladin$(): holy plate, maces, shields.'
             '$(li)$(l)Priest$(): healer with holy wands.'
             '$(li)$(l)Rogue$(): daggers and stealth.'
             '$(li)$(l)Warrior$(): double axes and glaives.'),
        text('$(li)$(l)Berserker$(): heavy axes and fury.'
             '$(li)$(l)Forcemaster$(): fists and force.'
             '$(li)$(l)Archers$(): Archer, Deadeye, Tundra Hunter, War Archer.'
             '$(li)$(l)Bard$(): songs that help the group, lutes and rapiers.'
             '$(li)$(l)Artillerist$(): mortars, mines, traps and bombs from the Siege Manual; flintlocks and '
             'repeating crossbows. Flintlock shots burn fire runes.'),
    ]),
    ('merchants', 'Class Merchants', 'minecraft:emerald', [
        text('Villages have buildings for some callings, each with a merchant who sells class gear:'
             '$(li)Wizard Tower: wizards and mages'
             '$(li)Sanctuary: paladins and priests'
             '$(li)Barracks: rogues and warriors'
             '$(li)Archery Range: archers'
             '$(li)Pub: bards$(br2)Not every village has every building. Merchants also buy crafted goods.'),
    ]),
]

E['professions'] = [
    ('jobs', 'Jobs', 'minecraft:iron_pickaxe', [
        text(f'Press {k("key.jobsplus.open_menu")} to open the Jobs menu and join two jobs. A job levels up '
             'from its own work and pays one $(item)job coin$() per level.$(br2)Spend coins in the same menu '
             'on power-ups, or on a third job.'),
        text('The ten jobs: Alchemist, Builder, Digger, Enchanter, Farmer, Fisherman, Hunter, Lumberjack, '
             'Miner and Smith.$(br2)Four of them also $(l)make$() things nobody else can: Smith, Hunter, '
             'Enchanter and Alchemist.'),
    ]),
    ('gates', 'Crafting Gates', 'minecraft:anvil', [
        text('Class gear by tier:$(li)Tier 1 at job level 10$(li)Diamond tier 2 at 20$(li)Netherite tier 3 '
             'at 25$(li)Armory sets at 30$(br2)$(l)Smith$(): plate armor and melee weapons. '
             '$(l)Hunter$(): leather armor, bows, crossbows, flintlocks, spears, pikes, quivers. $(l)Enchanter$(): robes, staves, '
             'wands, instruments.'),
        text('$(l)Enchanter$() shelves: Hellshelf and Seashelf at 10, their upgrades at 20, deep and sculk '
             'shelves at 25, endshelves at 30.$(br)$(l)Alchemist$(): Strong and Long potions at 10, Splash '
             'at 15, Lingering at 20.$(br)$(l)Smith$() reforging: Rare at 10, Epic at 20, Mythic at 30.'
             '$(br2)Hover over an item to see who makes it.'),
    ]),
    ('anyone', 'No Job? No Problem', 'minecraft:chest', [
        text('Gates only stop $(o)making$() things. Anyone can use, wear, repair and enchant them.$(br2)'
             'Class gear also drops from dungeons, monsters and bosses, class merchants sell it, plain '
             'bookshelves work for everyone, and a friend with the job can make it for you.'),
    ]),
    ('hunter', 'Hunter: Skinning', 'minecraft:leather', [
        text('A Hunter skins what they kill: leather, hides, bones, string and monster parts give Hunter '
             'experience. Plain monster kills give little or none, animals give a bit.$(br2)Every level adds a '
             '1% chance of an extra material (up to 40%), and a small chance of rarer parts.'),
        text('Hunters also level from leatherworking: leather, leather armor, saddles, bundles, item frames '
             'and small quivers.'),
    ]),
    ('xp', 'Other Ways to Level', 'minecraft:experience_bottle', [
        text('$(li)$(l)Smith$(): reforging, salvaging, socketing gems, smelting.'
             '$(li)$(l)Enchanter$(): enchanting, binding spells, cutting gems.'
             '$(li)$(l)Alchemist$(): brewing, runes, potion charms.'
             '$(li)$(l)Farmer$(): harvesting and cooking-pot meals.'
             '$(li)Miner, Digger, Lumberjack, Builder and Fisherman level from exactly what their name says.'),
    ]),
]

E['world'] = [
    ('zones', 'Zones', 'minecraft:grass_block', [
        text('The land itself has a danger level. Each level makes monsters hit about 10% harder and have '
             '15% more health. The name and level show on screen when you cross into a new zone.'
             '$(li)$(l)Hearthlands$() 1: plains, forests, meadows'
             '$(li)$(l)Wildlands$() 2: deserts, jungles, swamps, taigas, oceans'
             '$(li)$(l)Frontier$() 4: peaks, ice spikes, the deep dark'),
        text('$(li)$(l)Ashen Depths$() 5: the Nether'
             '$(li)$(l)Starless Reach$() 7: the End$(br2)Go further from the gentle lands only when your '
             'gear is ready for it.'),
    ]),
    ('dungeons', 'Dungeon Levels', 'minecraft:mossy_cobblestone', [
        text('Dungeons have their own level, shown when you step in: small ones 2, temples and forts 3, '
             'great dungeons 4, strongholds and ancient cities 5, Nether dungeons 6, End cities 7 and the '
             'Ruined Citadel 8.$(br2)Higher levels mean more spawners and better loot.'),
        text('$(l)No mining.$() The walls of many surface dungeons cannot be broken, so you have to go in '
             'through the door. Spawners, cobwebs, torches, leaves and plants still break, and chests open '
             'normally. Blocks you place inside cannot be broken again, so build carefully.'),
    ]),
    ('tiers', 'World Tiers', 'minecraft:nether_star', [
        text(f'Your $(item)world tier$() ({k("key.apotheosis.open_world_tier_select")} to look) makes '
             'monsters tougher and gear better. It rises by itself and never goes down:'
             '$(li)$(l)Haven$(): from the start'
             '$(li)$(l)Venture$(): Geode Claw'
             '$(li)$(l)Ascent$(): Nether Sigil'
             '$(li)$(l)Summit$(): Void Shard'
             '$(li)$(l)Pinnacle$(): Citadel Keystone and Dragonscale'),
    ]),
    ('elites', 'Elites and Invaders', 'minecraft:wither_skeleton_skull', [
        text('$(l)Elites$() are monsters with a colored title and extra powers: tougher, but they drop more. '
             'The deadliest kinds only appear in dangerous zones. Animals, villagers and bosses are never '
             'elites.$(br2)$(l)Invaders$() are rare named champions that roam the world. They hit hard and '
             'carry good gear.'),
    ]),
]

E['bosses'] = [
    ('chapters', 'Three Chapters', 'minecraft:map', [
        text('$(l)Chapter 1, the Overworld$(): the Amethyst Crab, then the Wildlands bosses (Ancient Remnant, '
             'Maledictus, the Leviathan), then $(l)The Harbinger$() in the Frontier.$(br2)'
             '$(l)Chapter 2, the Nether$(): the Netherite Monstrosity, then $(l)Ignis$().'),
        text('$(l)Chapter 3, the End$(): the Ender Dragon and the $(l)Ender Guardian$(). The Wither is an '
             'optional group raid.$(br2)Optional Overworld bosses: the Ferrous Wroughtnaut, the Frostmaw and '
             'Umvuthi.'),
    ]),
    ('sigil', 'The Nether Sigil', 'minerpg:nether_sigil', [
        spotlight('minerpg:nether_sigil',
                  'Fire alone never opens a Nether portal here. Use the $(item)Nether Sigil$() on a finished, '
                  'empty obsidian frame instead. It is never used up.$(br2)Dropped by The Harbinger to '
                  'everyone nearby. Inside the Nether, normal fire works, so you can always build a way home.'),
    ]),
    ('shard', 'The Void Shard', 'minerpg:void_shard', [
        spotlight('minerpg:void_shard',
                  'Eyes of Ender need a $(item)Void Shard$(): ender pearl, blaze powder and the shard. The shard '
                  'stays in the grid, so one makes every eye you need.$(br2)Dropped by Ignis to everyone '
                  'nearby.'),
    ]),
    ('trophies', 'Trophies', 'minerpg:trophy_amethyst_crab', [
        text('Every boss gives each player nearby (64 blocks) their own $(item)trophy$() when it falls. Quests '
             'check for trophies, so the whole group gets credit, not only whoever landed the last hit.'
             '$(br2)Keep them: some raise your world tier.'),
        text('$(li)Amethyst Crab: Geode Claw$(li)Ancient Remnant: Sun-Bleached Fang$(li)Maledictus: '
             'Frostbound Crown$(li)Leviathan: Abyssal Scale$(li)Netherite Monstrosity: Molten Heart'
             '$(li)Ender Guardian: Citadel Keystone$(li)Ender Dragon: Dragonscale$(li)Wither: Ashen Skull '
             'Shard'),
        text('Optional Overworld bosses:$(li)Ferrous Wroughtnaut: Wrought Rivet$(li)Frostmaw: Rimefang Tusk'
             '$(li)Umvuthi: Sunbird Plume'),
    ]),
    ('tips', 'Boss Tips', 'minecraft:totem_of_undying', [
        text('$(li)Bosses are built for a full party of four. Alone you will not win; bring your friends.'
             '$(li)Fights are long. Learn the big attacks and get out of the way: roll (R) makes you briefly '
             'untouchable.'
             '$(li)Quests hand out maps to the next lair.'
             '$(li)Bosses drop the best gear of each world tier.'),
    ]),
]

E['loot'] = [
    ('rarity', 'Rarity', 'minecraft:golden_sword', [
        text('Gear comes in five rarities, each with its own name color: $(l)Common, Uncommon, Rare, Epic, '
             'Mythic$(). Higher rarity means more bonus stats, called $(item)affixes$().$(br2)'
             'Chests and monsters drop up to Epic. Bosses drop Rare and better, and only bosses drop Mythic.'),
        text('Your world tier decides how good drops are. Monsters sometimes drop class gear of your tier, '
             'too.$(br2)Hold Shift over a piece of gear to compare it with what you wear.'),
    ]),
    ('sockets', 'Sockets and Gems', 'apotheosis:gem', [
        text('Weapons, staves and wands can roll $(item)sockets$(). Put a gem in at a smithing table; a '
             'Sigil of Socketing adds a socket. Armor has no sockets: for defensive gems, wear Jewelry rings '
             'and necklaces.'),
        text('The $(item)Arcanist\'s Prism$() is a gem for staves and wands only: it adds spell power. Look '
             'for it in boss and dungeon loot.'),
    ]),
    ('reforging', 'Salvage and Reforge', 'apotheosis:mysterious_scrap_metal', [
        text('Break gear you do not need at a $(item)Salvaging Table$() for rarity materials.$(br2)At a '
             '$(item)Reforging Table$(), spend a rarity material and gem dust to reroll an item\'s affixes '
             'at that rarity. Reforging to Rare, Epic or Mythic needs Smith level 10, 20 or 30.'),
    ]),
]

E['party'] = [
    ('party_hud', 'The Party', 'minecraft:cake', [
        text(f'Press {k("key.partyhud.open_screen")} to invite friends. In the Members tab, add each friend '
             'to favorites to see their health frames.$(br2)Party members share talent experience within 200 '
             'blocks, and your spells and swings never hurt each other. Heals and buffs reach every player.'),
        text('Your quest book stays your own. Boss trophies and key items go to everyone nearby, so nobody '
             'falls behind.$(br2)Set a waystone to Team to share it with your party.'),
    ]),
    ('revive', 'Downed, Not Dead', 'minecraft:golden_apple', [
        text('With other players online, a killing blow leaves you $(item)downed$() for 60 seconds. A friend '
             'revives you by holding the use key on you for 3 seconds; you get up with a few hearts and some '
             'weakness.$(br2)Heal spells cannot reach a downed player. Lava and the void still kill at once.'),
    ]),
]

KEYS = [
    ('key.ftbquests.quests', 'Quest book'),
    ('key.puffish_skills.open', 'Talents'),
    ('key.jobsplus.open_menu', 'Jobs'),
    ('key.partyhud.open_screen', 'Party'),
    ('key.neoorigins.skill_1', 'Racial power'),
    ('key.neoorigins.view_info', 'Your folk'),
    ('keybinds.combat_roll.roll', 'Combat roll'),
    ('key.curios.open.desc', 'Accessories'),
    ('key.apotheosis.open_world_tier_select', 'World tier'),
    ('key.advancements', 'Advancements'),
]
KEYS_2 = [
    ('key.travelersbackpack.inventory', 'Backpack'),
    ('key.travelersbackpack.cycle_tool', 'Backpack tool swap'),
    ('key.toms_storage.open_terminal', 'Storage terminal'),
    ('gui.xaero_pac_key_open_menu', 'Land claims'),
    ('keybindings.spell_engine.bypass_spell_hotbar', 'Normal hotbar'),
    ('key.cataclysm.ability', 'Weapon ability'),
    ('key.cataclysm.helmet_ability', 'Helmet ability'),
    ('key.cataclysm.chestplate_ability', 'Chestplate ability'),
    ('key.cataclysm.boots_ability', 'Boots ability'),
]

E['keys'] = [
    ('keys', 'Keys', 'minecraft:tripwire_hook', [
        text(''.join(f'$(li){label}: {k(b)}' for b, label in KEYS)),
        text(''.join(f'$(li){label}: {k(b)}' for b, label in KEYS_2)),
        text('$(li)Right-click a downed friend (hold) to revive.'
             '$(li)Hotbar keys cast spells while you hold a spell weapon.'
             '$(li)Shift over gear: compare with what you wear; Shift over an enchantment: what it does.'
             '$(br2)Rebind anything in Options > Controls. This page follows your changes.'),
    ]),
]


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main():
    if os.path.isdir(BOOK):
        shutil.rmtree(BOOK)
    write(os.path.join(BOOK, 'book.json'), {
        'name': "Adventurer's Handbook",
        'landing_text': 'Everything this world does differently, in short pages. Start with $(l)Getting Started$().',
        'subtitle': 'minerpg',
        'version': 1,
        'model': 'patchouli:book_brown',
        'book_texture': 'patchouli:textures/gui/book_brown.png',
        'show_progress': False,
        'show_toasts': False,
        'i18n': False,
        'pause_game': False,
        'text_overflow_mode': 'resize',
        'creative_tab': 'minecraft:tools_and_utilities',
    })
    cat_ids = set()
    for sort, (cid, name, desc, icon) in enumerate(CATEGORIES):
        cat_ids.add(cid)
        write(os.path.join(BOOK, 'en_us', 'categories', cid + '.json'),
              {'name': name, 'description': desc, 'icon': icon, 'sortnum': sort})
    count = 0
    for cid, entries in E.items():
        assert cid in cat_ids, cid
        for sort, (eid, name, icon, pages) in enumerate(entries):
            write(os.path.join(BOOK, 'en_us', 'entries', cid, eid + '.json'), {
                'name': name, 'icon': icon, 'category': f'{NS}:{cid}', 'sortnum': sort, 'pages': pages})
            count += 1
    print(f'{BOOK_ID}: {len(CATEGORIES)} categories, {count} entries')


if __name__ == '__main__':
    main()
