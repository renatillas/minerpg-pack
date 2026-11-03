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
# Field Guide advancements (see FIELD_GUIDE below). tools/gen_quests.py owns the rest of
# kubejs/data/minerpg/advancement/ and leaves this subfolder alone.
GUIDE_ADV = os.path.join(ROOT, 'kubejs', 'data', 'minerpg', 'advancement', 'field_guide')
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
    ('field_guide', 'Field Guide', 'Foes and places, written in as you find them.', 'minecraft:writable_book'),
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
        text('$(li)Choose your folk.'
             f'$(li)Open the quest book ({k("key.ftbquests.quests")}) and claim $(item)Choose Your Calling$(): your class kit.'
             '$(li)Tome in its slot, weapon in hand, cast.'
             f'$(li)Join two jobs ({k("key.jobsplus.open_menu")}).'
             f'$(li)Find your friends ({k("key.partyhud.open_screen")}).'),
        text('You wake in a plains village with a map to the nearest tavern. For your first three minutes the '
             'world goes easy on you: take the time to look around.$(br2)The $(item)gazebo$() holds a Spell '
             'Binding Table, the class buildings sell gear for your calling, and the waystone brings you home '
             'from anywhere. The Hearthlands around you are the gentlest land there is.'),
    ]),
    ('house_rules', 'House Rules', 'minecraft:red_bed', [
        text('A few rules make life easier for a small group:'
             '$(li)One sleeper is enough to skip the night.'
             '$(li)No phantoms.'
             '$(li)Creepers, ghast fireballs and wither skulls do not break blocks. Endermen do not pick blocks up.'
             '$(li)Villagers still farm, sheep still eat grass.'
             '$(li)An axe fells a whole tree at once; sneak to cut a single log.'),
        text('$(li)Nothing is lost when you die: it waits in your $(item)grave$() (see Party). With friends online '
             'you fall $(item)downed$() first, and they can pick you up.'
             '$(li)Dungeon chests are personal: everyone finds their own loot in the same chest.'
             '$(li)Mining is blocked inside many surface dungeons (see World & Danger).'
             '$(li)The small buttons beside any chest and your inventory sort it (or press R). A tool or stack '
             'that runs out is refilled from your bag.'),
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
             '$(li)$(l)Bard$(): songs that help the group, lutes and rapiers.'),
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
    ('market', 'The Market', 'coins:gold_coin', [
        text('The spawn village has a $(l)market$(): one stall for each job, selling supplies and rare goods '
             'for $(item)Gold Coins$(). The stock never runs out.$(br2)A stall gives $(l)25% off$() to members '
             'of its own job, so a friend with the right job can buy for you.'),
        text('$(l)Player shops$(): craft a $(item)Vending Machine$() or another shop block, fill it and set '
             'your prices in coins. Friends buy even while you are away, and the coins wait inside until you '
             'collect them.$(br2)Put coins in the slots on the shop screen to pay; change comes back there. Don\'t '
             'link a shop to a bank account: there is no way to take coins out of one.'),
    ]),
    ('jobs', 'Jobs', 'minecraft:iron_pickaxe', [
        text(f'Press {k("key.jobsplus.open_menu")} to open the Jobs menu and join two jobs. A job levels up '
             'from its own work and pays one $(item)Gold Coin$() per level.$(br2)Two jobs is the most anyone can '
             'hold. To swap one, type $(thing)/leavejob <job>$(): it costs 5 gold and deletes that job\'s level '
             'and power-ups for good.'),
        text('$(l)Coins$() are the money of the realm: 9 $(item)Copper$() make 1 $(item)Iron$(), 9 Iron make 1 '
             '$(item)Gold$() (change them at a crafting table).$(br2)They come from job levels, quests, chests, '
             'dungeons and bosses. The Jobs menu counts the coins you carry, in gold, and buying a power-up takes '
             'them from your inventory, with change given back.'),
        text('The nine jobs: Alchemist, Cook, Enchanter, Explorer, Farmer, Hunter, Jeweler, Miner and Smith.'
             '$(br2)Seven of them also $(l)make$() things nobody else can: Smith, Hunter, Enchanter, Jeweler, '
             'Alchemist, Cook and Explorer.'),
    ]),
    ('gates', 'Crafting Gates', 'minecraft:anvil', [
        text('Class gear by tier:$(li)Tier 1: anyone can craft it$(li)Diamond tier 2 at job level 10$(li)Netherite tier 3 '
             'at 20$(li)Armory sets at 25$(br2)$(l)Smith$(): plate armor and melee weapons. '
             '$(l)Hunter$(): leather armor, bows, crossbows, spears, quivers. $(l)Enchanter$(): robes, staves, '
             'wands, instruments.'),
        text('$(l)Enchanter$() shelves: Hellshelf and Seashelf at 10, their upgrades at 20, deep and sculk '
             'shelves at 25, endshelves at 30.$(br)$(l)Alchemist$(): Strong and Long potions at 10, Splash '
             'at 15, Lingering at 20.$(br)$(l)Smith$() reforging: Rare at 10, Epic at 20, Mythic at 30.'
             '$(br2)Hover over an item to see who makes it.'),
        text('$(l)Jeweler$(): gold and gem jewelry at 10, Socket Mounts at 15, diamond and emerald jewelry at '
             '20, netherite jewelry at 25. Copper and iron rings are free.$(br2)The Jeweler villager sells rings '
             'and necklaces, and dungeons hide them.'),
        text('$(l)Cook$(): plated meals at 10, feasts at 20. Cooking pot meals are free for everyone.'
             '$(br2)$(l)Explorer$(): scrolls and Crypt Survey Maps at 10, Warp Stones and Sharestones at 15, '
             'Waystones, Portstones and Great Dungeon maps at 20, Warp Plates at 25, Boss Lair maps at 30.'),
    ]),
    ('explorer', 'Explorer: Survey Maps', 'minecraft:filled_map', [
        text('A $(item)Survey Map$() becomes a map to the nearest place of its kind when you use it: a '
             'settlement, a crypt, a great dungeon or a boss lair. Anyone can draw a Settlement map (map and '
             'emerald); the others need an Explorer.$(br2)Copy the finished map at a cartography table for the '
             'whole party.'),
        text('Explorers also build the travel network. $(item)Sharestones$() of one color all link to each '
             'other, $(item)Warp Plates$() pair up, and scrolls are one-use trips.$(br2)Waystones you find in '
             'the world stay free for everyone.'),
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
        text('Wild game counts too: deer, boars, bears, turkeys, mammoths and more drop hides, fur, fat, teeth '
             'and antlers.$(br2)Hunters also level from leatherworking (leather, leather armor, saddles, bundles, '
             'item frames, small quivers, knapsacks) and from foraging: breaking mushroom stumps and trunks.'),
    ]),
    ('xp', 'Other Ways to Level', 'minecraft:experience_bottle', [
        text('$(li)$(l)Smith$(): reforging, salvaging, smelting.'
             '$(li)$(l)Enchanter$(): enchanting at the table or with books at the anvil, binding spells.'
             '$(li)$(l)Jeweler$(): jewelry, cutting gems, sockets and setting gems.'
             '$(li)$(l)Alchemist$(): brewing (Apothecary potions too), runes, potion charms.'
             '$(li)$(l)Cook$(): every meal (pot, table, furnace, smoker, campfire or stove) and keg drink, more for '
             'each new dish.'
             '$(li)$(l)Explorer$(): each new biome, place and waystone, filling in maps, maps, atlases and travel '
             'items.'
             '$(li)$(l)Farmer$(): harvesting, planting, breeding.'
             '$(li)Miners level from stone, ores and geode crystals.'),
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
        text('$(l)Dungeon kinds.$() Some dungeons have a temper, named on the zone line:'
             '$(li)$(l)Armored$(): forts and garrisons. Defenders wear heavy armor; weapons and arrows bite less, '
             'spells cut straight through.'
             '$(li)$(l)Magebane$(): witch houses, sanctuaries, plague halls. Warded against spells; steel works.'
             '$(li)$(l)Bounty$(): bandit and pirate haunts. A little meaner, and worth far more experience.'),
    ]),
    ('travel', 'Waystones and Travel', 'waystones:waystone', [
        text('Activate every $(item)waystone$() you pass. From any waystone you can travel to any other you know.'
             '$(br2)A trip costs a little experience: 1 point per 100 blocks, at most 27 points, a flat 27 to another '
             'dimension. Warp plates, scrolls and global waystones are free.'),
        spotlight('waystones:warp_stone',
                  'The $(item)Warp Stone$() is your way home: hold it to travel to any waystone you know, from '
                  'anywhere, for free. It never wears out, but it needs 5 minutes to recover after each use.'
                  '$(br2)The quest $(item)A Stone of Your Own$() gives you one.'),
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
             '$(li)Quests hand out maps to the next lair, and the Field Guide fills in as you find them.'
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
             'Sigil of Socketing adds a socket. Armor takes no Apotheosis gems.'),
        text('Armor has its own $(item)jeweler\'s sockets$(): combine a piece with a Socket Mount at an anvil, '
             'then with a gem cut at the Jeweler\'s Kit. One per piece.$(br2)Rings and necklaces carry gems '
             'too.'),
        text('The $(item)Arcanist\'s Prism$() is a gem for staves and wands only: it adds spell power. Look '
             'for it in boss and dungeon loot.'),
    ]),
    ('reforging', 'Salvage and Reforge', 'apotheosis:mysterious_scrap_metal', [
        text('Recycle what you do not need at a $(item)Salvaging Table$(). Class weapons, armor, quivers '
             'and jewelry give back part of their materials; relics give rarity materials by grade; gear '
             'with a rarity also gives its rarity material. Unique weapons always have a rarity. Spell books, '
             'scrolls, song sheets and upgrade crystals cannot be recycled.'),
        text('At a '
             '$(item)Reforging Table$(), spend a rarity material and gem dust to reroll an item\'s affixes '
             'at that rarity. Reforging to Rare, Epic or Mythic needs Smith level 10, 20 or 30.'),
    ]),
]

E['party'] = [
    ('party_hud', 'The Party', 'minecraft:cake', [
        text(f'Press {k("key.partyhud.open_screen")} to invite friends. In the Members tab, add each friend '
             'to favorites to see their health frames.$(br2)Party members share talent experience within 200 '
             'blocks, and your spells, arrows and swings never hurt each other. Heals and buffs reach every player.'),
        text('Your quest book stays your own. Boss trophies and key items go to everyone nearby, so nobody '
             'falls behind.$(br2)Set a waystone to Team to share it with your party.'),
    ]),
    ('revive', 'Downed, Not Dead', 'minecraft:golden_apple', [
        text('With other players online, a killing blow leaves you $(item)downed$() for 60 seconds. A friend '
             'revives you by holding the use key on you for 3 seconds; you get up with a few hearts and some '
             'weakness.$(br2)Heal spells cannot reach a downed player. Lava and the void still kill at once.'),
    ]),
    ('graves', 'Graves', 'minecraft:skeleton_skull', [
        text('Die for real and a $(item)grave$() rises where you fell. It holds everything you carried: your '
             'inventory, armor, accessories, backpack and experience. Nothing is lost.$(br2)Chat tells you where '
             'it is, and you respawn with a compass that points to it. Right-click the grave to take it all back.'),
        text('Only you can open your grave at first. After 15 minutes a friend can collect it for you, and you are '
             'told who did.$(br2)Being $(item)downed$() makes no grave: a grave only comes with a real death.'),
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


# --------------------------------------------------------------------------------------
# Field Guide: one locked entry per boss and per kind of great place. An entry opens when you
# first see the place or its master ("sighted"); its last page opens when the master falls
# ("defeated"). Both are hidden advancements (minerpg:field_guide/...), so each unlock shows one
# quiet vanilla advancement toast (task frame: no sound, nothing in chat). Patchouli only knows
# advancements the client has been sent, and the game only sends ones with a display, which is
# why these have one (hidden until earned) and the book's own toasts stay off.
#
# Sighted = stepping into the lair (location check, chunk-local, no structure search), OR the
# boss in line of sight within 32 blocks (kubejs/server_scripts/minerpg_field_guide.js awards
# the "seen" criterion), OR its trophy (late arrivals). Defeated = holding the trophy/key item
# (everyone nearby at the kill gets one), or landing the killing blow yourself.
#
# Counter tips match the pack as built (pack 0.8.0 boss balance): bosses are built for a party
# of four, hits are heavy, a combat roll is briefly untouchable, and the Ender Guardian, Umvuthi
# and the Dragon regenerate during the fight.
# --------------------------------------------------------------------------------------
# (key, entity id, name, icon, sighted extra criteria, defeated item, lore, counter, advice, after)
def in_structure(structure):
    return {'trigger': 'minecraft:location', 'conditions': {'player': [{
        'condition': 'minecraft:entity_properties', 'entity': 'this',
        'predicate': {'location': {'structures': structure}}}]}}


GUIDE_BOSSES = [
    ('amethyst_crab', 'cataclysm:amethyst_crab', 'The Amethyst Crab', 'minerpg:trophy_amethyst_crab',
     {'lair': in_structure('cataclysm:amethyst_nest')}, 'minerpg:trophy_amethyst_crab',
     'A crab the size of a cart, armored in living crystal. It keeps the $(l)Amethyst Nest$() deep in the lush '
     'caves of the Hearthlands.',
     'It mends faster the healthier it is. Hit hard from the first second and never let up; a slow party '
     'never finishes it.',
     'Light the cave before you wake it.',
     'Its $(item)Geode Claw$() raises your world tier to Venture.'),
    ('ferrous_wroughtnaut', 'mowziesmobs:ferrous_wroughtnaut', 'The Ferrous Wroughtnaut', 'minerpg:trophy_ferrous_wroughtnaut',
     {'lair': in_structure('mowziesmobs:wrought_chamber')}, 'minerpg:trophy_ferrous_wroughtnaut',
     'An empty suit of armor that still swings its axe, sealed in a chamber under the Hearthlands.',
     'Blows on its front plate do next to nothing. Let the axe miss, then strike its back while it hauls the '
     'blade free.',
     'This fight is about timing, not damage. Watch before you swing.',
     'Its $(item)Wrought Rivet$() counts for the quest book.'),
    ('umvuthi', 'mowziesmobs:umvuthi', 'Umvuthi, the Sunbird', 'minerpg:trophy_umvuthi',
     {'lair': in_structure('mowziesmobs:umvuthana_grove')}, 'minerpg:trophy_umvuthi',
     'Chief of the masked Umvuthana, holding court in a grove of the savanna.',
     'He heals all fight long and hides behind his followers. Clear the masks around him, then keep every '
     'blade on him so the healing never catches up.',
     'Sunfire lands where you stand. Keep moving.',
     'Its $(item)Sunbird Plume$() counts for the quest book.'),
    ('frostmaw', 'mowziesmobs:frostmaw', 'The Frostmaw', 'minerpg:trophy_frostmaw',
     {'lair': in_structure('mowziesmobs:frostmaw_spawn')}, 'minerpg:trophy_frostmaw',
     'A great white beast asleep among the snowfields and ice spikes.',
     'Its breath freezes everything in front of it, and it slams anyone who crowds it. Fight from its flanks '
     'and roll the slam.',
     'It sleeps until disturbed. Wake it only when the whole party is ready.',
     'Its $(item)Rimefang Tusk$() counts for the quest book.'),
    ('ancient_remnant', 'cataclysm:ancient_remnant', 'The Ancient Remnant', 'minerpg:trophy_ancient_remnant',
     {'lair': in_structure('cataclysm:cursed_pyramid')}, 'minerpg:trophy_ancient_remnant',
     'The bones of a sun-king, still crowned, at the bottom of the $(l)Cursed Pyramid$() in the deserts of the '
     'Wildlands.',
     'It charges in straight lines. Roll aside late and punish it while it turns.',
     'Never fight it in a corridor. Give yourselves room to step aside.',
     'Its $(item)Sun-Bleached Fang$() counts for the quest book, and its quest marks the way to the Frontier.'),
    ('maledictus', 'cataclysm:maledictus', 'Maledictus', 'minerpg:trophy_maledictus',
     {'lair': in_structure('cataclysm:frosted_prison')}, 'minerpg:trophy_maledictus',
     'A prisoner who became the prison, held in the black ice of the $(l)Frosted Prison$().',
     'Its smashes hit everything close by. Spread out, so one blow never finds the whole party.',
     'Keep a way out behind you.',
     'Its $(item)Frostbound Crown$() counts for the quest book, and its quest marks the way to the Frontier.'),
    ('leviathan', 'cataclysm:the_leviathan', 'The Leviathan', 'minerpg:trophy_leviathan',
     {'lair': in_structure('cataclysm:sunken_city')}, 'minerpg:trophy_leviathan',
     'A serpent of the deep, coiled in a flooded hall of the $(l)Sunken City$().',
     'Out of the water it cannot be touched. Fight it in its element, and bring water breathing for '
     'everyone.',
     'Carry more air than you think you need.',
     'Its $(item)Abyssal Scale$() counts for the quest book, and its quest marks the way to the Frontier.'),
    ('scylla', 'cataclysm:scylla', 'Scylla', 'minecraft:trident',
     {'lair': in_structure('cataclysm:acropolis')}, None,
     'A storm-crowned terror ruling the $(l)Acropolis$(), high above the warm seas.',
     'She strikes in wide sweeping arcs and calls lightning. Step out of reach, then close in when the sweep '
     'ends.',
     'No quest asks for her. Go for the loot and the story.',
     'Fallen. The warm seas are a little quieter.'),
    ('harbinger', 'cataclysm:the_harbinger', 'The Harbinger', 'minerpg:nether_sigil',
     {'lair': in_structure('cataclysm:ancient_factory')}, 'minerpg:nether_sigil',
     'The iron herald of the $(l)Ancient Factory$(), deep under the mountains of the Frontier.',
     'It repairs itself whenever you hesitate. Keep the pressure on, and break line of sight when its beams '
     'sweep the hall.',
     'Bring the whole party and your best gear. It holds the way to the Nether.',
     'Everyone nearby earns a $(item)Nether Sigil$(): it opens Nether portals and raises your world tier to '
     'Ascent.'),
    ('netherite_monstrosity', 'cataclysm:netherite_monstrosity', 'The Netherite Monstrosity', 'minerpg:trophy_netherite_monstrosity',
     {'lair': in_structure('cataclysm:soul_black_smith')}, 'minerpg:trophy_netherite_monstrosity',
     'A forge-born giant of netherite and lava that guards the Soul Blacksmith\'s forge in the Nether.',
     'Its smash shakes the floor and leaves fire behind. Roll the smash, and never stand in its lava.',
     'Bring fire resistance. Everything here burns.',
     'Its $(item)Molten Heart$() counts for the quest book, and the kill earns a talent point.'),
    ('ignis', 'cataclysm:ignis', 'Ignis', 'minerpg:void_shard',
     {'lair': in_structure('cataclysm:burning_arena')}, 'minerpg:void_shard',
     'A fallen knight wrapped in fire, waiting in the $(l)Burning Arena$().',
     'Its sword hits hard enough to drop a careless caster. Healers stay back; fighters roll through the big '
     'swings.',
     'It grows fiercer as it weakens. Save your strongest spells for the end.',
     'Everyone nearby earns a $(item)Void Shard$(): Eyes of Ender need it, and it raises your world tier to '
     'Summit.'),
    ('ender_guardian', 'cataclysm:ender_guardian', 'The Ender Guardian', 'minerpg:trophy_ender_guardian',
     {'lair': in_structure('cataclysm:ruined_citadel')}, 'minerpg:trophy_ender_guardian',
     'The last warden of the $(l)Ruined Citadel$(), at the edge of the void.',
     'It heals the whole fight. Keep your damage steady; a party that stops to regroup gives back everything '
     'it took.',
     'Its blows can throw you far. Fight away from the edges.',
     'Its $(item)Citadel Keystone$(), with the Dragonscale, raises your world tier to Pinnacle.'),
    ('wither', 'minecraft:wither', 'The Wither', 'minerpg:trophy_wither',
     {'summoned': {'trigger': 'minecraft:summoned_entity', 'conditions': {'entity': [{
         'condition': 'minecraft:entity_properties', 'entity': 'this', 'predicate': {'type': 'minecraft:wither'}}]}}},
     'minerpg:trophy_wither',
     'A three-headed horror you build yourself, from soul sand and wither skeleton skulls.',
     'Below half health it shrugs off arrows and bolts. Archers, bring a blade for the second half.',
     'Summon it far from anything you love. It smashes blocks when it is hurt.',
     'Its $(item)Ashen Skull Shard$() counts for the quest book.'),
    ('ender_dragon', 'minecraft:ender_dragon', 'The Ender Dragon', 'minerpg:trophy_ender_dragon',
     {'arrived': {'trigger': 'minecraft:changed_dimension', 'conditions': {'to': 'minecraft:the_end'}}},
     'minerpg:trophy_ender_dragon',
     'The last dragon, circling the island at the heart of the End.',
     'The crystals on the pillars heal it. Break them first, then stay out of its purple breath: it eats '
     'through any armor.',
     'It also heals slowly by itself. Once you start, do not stop.',
     'Its $(item)Dragonscale$(), with the Citadel Keystone, raises your world tier to Pinnacle.'),
]

# (key, name, icon, structure or #tag, lore, counter, advice)
GUIDE_PLACES = [
    ('small_dungeons', 'Crypts and Cellars', 'minecraft:mossy_cobblestone', '#minerpg:small_dungeons',
     'Small dungeons under the fields and forests: crypts, spider dens and old cellars. Dungeon level 2.',
     'Break the spawner first. The room empties fast after that.',
     'A good first trip for a new party.'),
    ('great_dungeons', 'Great Dungeons', 'minecraft:cracked_stone_bricks', '#minerpg:wildlands_dungeons',
     'Forts, temples, towers, ruins and wrecked ships across the Wildlands. Dungeon level 3 or 4, higher in '
     'the Frontier.',
     'The walls will not break. Take the door and clear room by room.',
     'Some are $(l)Armored$(), $(l)Magebane$() or $(l)Bounty$() dungeons. The zone line tells you which; '
     'see World & Danger.'),
    ('ancient_cities', 'Ancient Cities', 'minecraft:sculk_shrieker', 'minecraft:ancient_city',
     'Silent cities in the deep dark of the Frontier. Dungeon level 5.',
     'Noise wakes the Warden. Sneak, and never fight it for nothing.',
     'Wool muffles your steps. Bring some.'),
    ('strongholds', 'The Stronghold', 'minecraft:end_portal_frame', '#minerpg:strongholds',
     'A maze of stone under the Overworld, built around the portal to the End. Dungeon level 5.',
     'Follow a thrown Eye of Ender; the portal room is near the bottom.',
     'Mark your way back. Every corridor looks the same.'),
    ('nether_fortresses', 'Nether Fortresses', 'minecraft:nether_bricks', '#minerpg:nether_fortresses',
     'Dark brick bridges over the lava seas. Dungeon level 6.',
     'Blazes fly out of reach: bring a bow or spells. Wither skeletons hit hard and wither you.',
     'The fortress gardens grow nether wart.'),
    ('bastions', 'Bastions', 'minecraft:gilded_blackstone', 'minecraft:bastion_remnant',
     'Black fortresses where piglins hoard their gold. Armored dungeon, level 6.',
     'Brutes ignore gold and wear heavy armor. Spells cut straight through it.',
     'Wear one piece of gold, or every piglin turns on you.'),
    ('nether_keeps', 'Nether Keeps', 'minecraft:polished_blackstone_bricks', '#minerpg:nether_dungeons',
     'Keeps, donjons, ports and skeleton towers scattered through the wastes. Dungeon level 6.',
     'Fight at the doors. The halls are narrow and crowded.',
     'Fire resistance makes every trip here easier.'),
    ('end_cities', 'End Cities', 'minecraft:purpur_block', 'minecraft:end_city',
     'Purple towers on the outer islands of the End. Dungeon level 7.',
     'Shulker bullets lift you into the air. Slow falling, or a block under your feet, saves a long drop.',
     'Some cities have a ship moored alongside. Look aboard.'),
    ('end_castles', 'End Castles', 'minecraft:end_stone_bricks', '#minerpg:end_dungeons',
     'Castles, lighthouses and ships on the outer islands. Up to dungeon level 8, the deadliest places there are.',
     'Clear the courtyard before you climb. Nothing here forgives a fall.',
     'Go only with gear from the Summit tier or better.'),
]


def guide_advancement(path, title, desc, icon, criteria, parent='minerpg:field_guide/root'):
    write(os.path.join(GUIDE_ADV, path + '.json'), {
        'parent': parent,
        'display': {
            'icon': {'id': icon}, 'title': {'text': title}, 'description': {'text': desc},
            'frame': 'task', 'show_toast': True, 'announce_to_chat': False, 'hidden': True},
        'criteria': criteria,
        'requirements': [sorted(criteria)],  # any one criterion is enough
    })
    return 'minerpg:field_guide/' + path


def field_guide():
    """Writes the advancements and returns the Field Guide's book entries."""
    if os.path.isdir(GUIDE_ADV):
        shutil.rmtree(GUIDE_ADV)
    # The tab root: granted on join, never announced.
    write(os.path.join(GUIDE_ADV, 'root.json'), {
        'display': {
            'icon': {'id': 'minecraft:writable_book'}, 'title': {'text': 'Field Guide'},
            'description': {'text': 'Places found and foes faced. Read them in your handbook.'},
            'background': 'minecraft:textures/block/spruce_planks.png',
            'frame': 'task', 'show_toast': False, 'announce_to_chat': False, 'hidden': False},
        'criteria': {'joined': {'trigger': 'minecraft:tick'}},
    })
    entries = [('how', 'How the Field Guide Works', 'minecraft:writable_book', None, [
        text('Every great foe and every kind of dangerous place has a page here, locked until you earn it.'
             '$(li)Step into a lair, or set eyes on its master, and the page opens.'
             '$(li)Bring the master down and the last page fills in.$(br2)'
             'Each page ends with a $(l)Counter$(): the one thing to remember when the fight starts.'),
        text('Every master in this world is built for a full party of four. Its hits are heavy and its fights '
             f'are long. A combat roll ({k("keybinds.combat_roll.roll")}) makes you untouchable for a moment: '
             'learn the big blows and roll through them.$(br2)Pages you have not earned stay locked. Go and '
             'look.'),
    ])]
    for key, entity, name, icon, sight, item, lore, counter, advice, after in GUIDE_BOSSES:
        sighted_crit = dict(sight)
        sighted_crit['seen'] = {'trigger': 'minecraft:impossible'}  # awarded by minerpg_field_guide.js
        defeated_crit = {'killed': {'trigger': 'minecraft:player_killed_entity', 'conditions': {'entity': [{
            'condition': 'minecraft:entity_properties', 'entity': 'this', 'predicate': {'type': entity}}]}}}
        if item:
            defeated_crit['trophy'] = {'trigger': 'minecraft:inventory_changed',
                                       'conditions': {'items': [{'items': item}]}}
            sighted_crit['trophy'] = defeated_crit['trophy']
        sighted = guide_advancement(f'sighted/{key}', f'Sighted: {name}', 'A new page opens in your Field Guide.',
                                    icon, sighted_crit)
        defeated = guide_advancement(f'defeated/{key}', f'Defeated: {name}', 'The last page of its Field Guide entry is yours.',
                                     icon, defeated_crit, parent=sighted)
        last = text(f'$(l)Defeated.$()$(br2){after}')
        last['advancement'] = defeated
        entries.append((key, name, icon, sighted, [
            text(f'$(o){lore}$()$(br2)$(l)Counter:$() {counter}$(br2){advice}'), last]))
    for key, name, icon, structure, lore, counter, advice in GUIDE_PLACES:
        found = guide_advancement(f'found/{key}', f'Found: {name}', 'A new page opens in your Field Guide.',
                                  icon, {'entered': in_structure(structure)})
        entries.append((key, name, icon, found, [
            text(f'$(o){lore}$()$(br2)$(l)Counter:$() {counter}$(br2){advice}')]))
    return entries


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
    guide = field_guide()
    for sort, (eid, name, icon, lock, pages) in enumerate(guide):
        entry = {'name': name, 'icon': icon, 'category': f'{NS}:field_guide', 'sortnum': sort, 'pages': pages}
        if lock:
            entry['advancement'] = lock
        write(os.path.join(BOOK, 'en_us', 'entries', 'field_guide', eid + '.json'), entry)
    count += len(guide)
    print(f'{BOOK_ID}: {len(CATEGORIES)} categories, {count} entries ({len(guide)} in the Field Guide, '
          f'{len(GUIDE_BOSSES) * 2 + len(GUIDE_PLACES) + 1} advancements)')


if __name__ == '__main__':
    main()
