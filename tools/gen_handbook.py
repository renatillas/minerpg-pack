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
    ('home', 'Home & Hearth', 'Building a base: storage, furniture, the chisel and the Experience Obelisk.', 'handcrafted:oak_chair'),
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
             f'$(li)Join up to three jobs ({k("key.jobsplus.open_menu")}).'
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

# Pack 1.6.0 origins redesign (tools/gen_origins.py is the source of the numbers). Abilities are listed in key order:
# the first is on Skill 1, the second on Skill 2, the third on Skill 3.
RACES = [
    ('hearthfolk', 'Hearthfolk', 'minecraft:bell', 'Village folk, at home anywhere with a hearth.',
     ['One extra combat roll charge.', 'Villagers charge you about 25% less.'],
     ['Rally (90 s): you and players within 8 blocks gain Speed, Resistance and Regeneration for 10 seconds.',
      'Hearthstone (30 min): return to your bed.'],
     ['15% less damage in the Nether and the End.']),
    ('deepkin', 'Deepkin', 'minecraft:deepslate', 'Short, stout folk of the deepslate.',
     ['+4 armor and +2 hearts.', 'Mine 25% faster; night vision out of the sky\'s sight.',
      'Vein Miner: sneak while mining an ore to break the whole vein.', '+20% Earth spell power.'],
     ['Earthshatter (45 s): creatures within 6 blocks take 8 damage and fly up.'],
     ['Swim 40% slower.', '10% less damage under the open sky.']),
    ('grovekin', 'Grovekin', 'minecraft:flowering_azalea', 'Slender folk of the lush forests.',
     ['Climb any wall.', '+15% ranged damage.', '+15% Air spell power and Healing power.', '15% faster in forests.'],
     ['Entangle (90 s): creatures within 6 blocks are held in place for 5 seconds.'],
     ['2 hearts less.', '25% more fire damage taken.']),
    ('tuskborn', 'Tuskborn', 'minecraft:gilded_blackstone', 'Broad, tusked folk of the bastions.',
     ['+20% crit damage, +5% crit chance.', 'Below 30% health: Strength II and Resistance.',
      'Hard to knock back; piglins leave you alone (brutes do not).'],
     ['Charge (20 s): rush forward, hitting creatures in front for 6 damage.',
      'Battle Fury (2 min): Haste II and Strength for 15 seconds.'],
     ['20% less spell power.', 'Villagers charge you about 25% more.']),
    ('emberkin', 'Emberkin', 'minecraft:blaze_powder', 'Blaze-touched and fire-proof.',
     ['Immune to fire and lava; swim through lava.', 'Your hits set creatures alight.', '+20% Fire spell power.',
      'Phoenix: once every 20 minutes, a killing blow sets everything nearby alight and leaves you at 4 hearts.'],
     ['Fireball (20 s): a fire ball that burns creatures where it lands. It breaks no blocks.'],
     ['Water hurts you every second, rain every two.']),
    ('rimeborn', 'Rimeborn', 'minecraft:packed_ice', 'Kin of the ice spikes and the cold seas.',
     ['Walk on water (sneak to sink); immune to freezing and powder snow.', 'Swim 30% faster, hold your breath twice as long.',
      'Your hits slow creatures.', '+20% Frost and +15% Water spell power.'],
     ['Tidal Wave (30 s): icy water hits and slows creatures ahead and throws back those around you.'],
     ['Weakened in the Nether and hot biomes.', '25% more fire damage taken.']),
    ('voidborn', 'Voidborn', 'minecraft:ender_eye', 'Tall, quiet folk from the End.',
     ['+20% Arcane spell power.', 'Endermen do not mind your gaze.', 'Void Pocket: 9 slots of your own, kept when you die.'],
     ['Blink (30 s): teleport up to 12 blocks to where you look.',
      'Void Surge (20 s): a firework-like boost while gliding with an elytra.',
      'Void Pocket: open your pocket.'],
     ['Water hurts you (rain does not).']),
    ('gravebound', 'Gravebound', 'minecraft:soul_lantern', 'Undead of the soul sand valleys.',
     ['10% of the damage you deal heals you.', '+20% Rage power.', 'Monsters notice you later.'],
     ['Raise Dead (2 min): two skeleton warriors fight for you for 30 seconds.',
      'Feign Death (90 s): turn invisible; every creature after you loses track of you.'],
     ['All healing you receive is 30% weaker.']),
]
SKILL_KEYS = ['key.neoorigins.skill_1', 'key.neoorigins.skill_2', 'key.neoorigins.skill_3']


def race_entry(rid, name, icon, blurb, gifts, abilities, drawbacks):
    first = f'$(o){blurb}$()$(br2)$(l)Gifts$()' + ''.join(f'$(li){g}' for g in gifts)
    second = ('$(l)Abilities$()' + ''.join(f'$(li){k(SKILL_KEYS[n])}: {a}' for n, a in enumerate(abilities))
              + '$(br2)$(l)Drawbacks$()' + ''.join(f'$(li){d}' for d in drawbacks))
    return (rid, name, icon, [text(first), text(second)])


E['races'] = [
    ('folk', 'Choosing a Folk', 'neoorigins:orb_of_origin', [
        text('You pick your folk the first time you join. Each folk has a clear strength, one or two abilities '
             f'on {k("key.neoorigins.skill_1")} and {k("key.neoorigins.skill_2")}, a drawback you will feel, and its own '
             'size.$(br2)Abilities never hurt other players. Every class works with every folk, but each folk suits '
             'some classes best.'),
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
             'at a Spell Binding Table and swapping tomes. That is not the same as a $(l)Side Class$(): your talents '
             'follow one main class, and the Side Class tab adds a little of another on top.'),
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
             'shared with party members within 200 blocks.$(br2)Kills fill the class tree up to 18 points, '
             'each one slower than the last. The tree has more talents than that, so choose.'),
        text('The weapon tree holds 10 points.$(br2)The great bosses give $(l)Ascension$() points instead, for a '
             'tab of their own: see $(l)Ascension and Fates$().'),
        text('Changed your mind? An $(item)Orb of Oblivion$() resets your talents so you can spend them '
             'again, or on another class tree. It resets the Side Class tab too.'),
    ]),
    ('side_class', 'Side Class', 'spell_engine:spell_book', [
        text('Once your class tree has 9 points, a $(l)Side Class$() tab opens next to it. Pick any other class '
             'there and spend up to 8 points on it. The tab has its own experience bar, filled by the same kills '
             'as your class tree.$(br2)Your side class can never be your main class.'),
        text('Each side class offers its root, its first four tome spells, two upgrades for each, and four early '
             'passives. You can learn $(l)two$() of the four spells, and cast them with any weapon. A third is '
             'refused and its point comes back.$(br2)Arrow spells still need a bow, and caster spells still use '
             'runes. Tier-4 spells, Ascension and weapon talents stay with your main class.'),
        text('To change your side class or its spells, use an $(item)Orb of Oblivion$(): it resets all your '
             'talent tabs, the Side Class one included.'),
    ]),
    ('ascension', 'Ascension and Fates', 'minecraft:nether_star', [
        text('$(l)Ascension$() is a talent tab only bosses can fill. No experience counts.$(br2)Your first great '
             'Wildlands boss (Ancient Remnant, Maledictus or the Leviathan) opens it and gives your first point: '
             'your $(l)Fate$().'),
        text('$(li)Wildlands boss: a $(l)Fate$()$(li)The Harbinger: a $(l)Transformation$() of one spell'
             '$(li)Monstrosity and Ignis: two $(l)Deepenings$()$(li)Ender Guardian: your $(l)Ultimate$()'
             '$(li)Ender Dragon and the Wither: two $(l)Empowerments$() of it', 'The Ladder'),
        text('Each class has two Fates. Taking one locks the other, and each has a $(l)drawback$(). You get one of '
             'two Transformations and two of three Deepenings.$(br2)An $(item)Orb of Oblivion$() resets it all; '
             'points are kept.$(br2)Rogue, Warrior, Priest, Paladin and Deadeye have Fates now. Other classes keep '
             'their points until theirs arrive.', 'Choosing'),
        text('Your first melee hit after Vanish or Shadow Step deals +150% damage.$(br2)Drawback: -20% max health.$(br2)Ultimate: Thousand Cuts: blades hit every enemy within 6 blocks, every hit critical.', 'Nightblade (Rogue)'),
        text('Every melee hit adds a stack of Fatal Poison (up to 5).$(br2)Drawback: -20% melee damage.$(br2)Ultimate: Plague Bloom: a toxic cloud follows you for 8 seconds.', 'Plaguefang (Rogue)'),
        text('+30% max health, +4 armor. Charge makes enemies attack you.$(br2)Drawback: -15% movement and attack speed.$(br2)Ultimate: Colossus: 10 seconds larger, unmovable, taking half damage.', 'Juggernaut (Warrior)'),
        text('Mortal Strike deals double damage below 35% health; kills reset Charge.$(br2)Drawback: -30% healing received.$(br2)Ultimate: Rampage: for 8 seconds every kill resets your cooldowns.', 'Reaver (Warrior)'),
        text('Overhealing becomes a barrier. +30% healing power.$(br2)Drawback: -50% holy damage.$(br2)Ultimate: Dawnfall: your heals land on every ally near you, and death holds off once.', 'Lightbinder (Priest)'),
        text('40% of the holy damage you deal heals the most injured ally near you.$(br2)Drawback: -30% healing power on your heals.$(br2)Ultimate: Wrath of Dawn: pillars of light strike and heal.', 'Zealot (Priest)'),
        text('+20% max health. Shield blocks heal you and pull aggro.$(br2)Drawback: -25% attack damage.$(br2)Ultimate: Bastion of Light: a dome where allies take 60% less damage.', 'Bulwark (Paladin)'),
        text('Melee hits add holy damage from your healing power.$(br2)Drawback: -4 armor, -20% healing power.$(br2)Ultimate: Avatar of Light: wings, +30% attack damage, shockwaves.', 'Crusader (Paladin)'),
        text('+35% ranged damage to enemies 16+ blocks away.$(br2)Drawback: -30% ranged damage within 6 blocks.$(br2)Ultimate: Killshot: a shot through every enemy in a line that finishes off the wounded.', 'Sharpshooter (Deadeye)'),
        text('Taking damage leaves a decoy behind; Alter Ego comes back sooner.$(br2)Drawback: -20% max health.$(br2)Ultimate: Hall of Mirrors: six decoys, and your shots echo onto other enemies.', 'Phantom (Deadeye)'),
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
        text(f'Press {k("key.jobsplus.open_menu")} to open the Jobs menu and join up to three jobs. A job levels up '
             'from its own work and pays one $(item)Gold Coin$() per level.$(br2)Three jobs is the most anyone can '
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
             'wands, instruments.$(br2)Vanilla diamond and netherite swords and armor, and the boss-material '
             'sets (Ignitium, Cursium, Dragon Bones...), count as Smith tier 2 and 3 too.'),
        text('$(l)Enchanter$() shelves: Hellshelf and Seashelf at 10, their upgrades at 20, deep and sculk '
             'shelves at 25, endshelves at 30.$(br)$(l)Alchemist$(): Strong and Long potions at 10, Splash '
             'at 15, Lingering at 20.$(br)$(l)Smith$() reforging: Rare at 10, Epic at 20, Mythic at 30.'
             '$(br2)Hover over an item to see who makes it.'),
        text('$(l)Jeweler$(): gold and gem jewelry at 10, Socket Mounts at 15, diamond and emerald jewelry at '
             '20, netherite jewelry at 25. Copper and iron rings are free.$(br2)The Jeweler villager sells rings '
             'and necklaces, and dungeons hide them.'),
        text('$(l)Cook$(): plated meals and hearty dishes (4-5 ingredients) at 10, feasts and grand dishes (6 or more) at '
             '20. Simple dishes and cooking pot meals are free for everyone.'
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
             '$(li)$(l)Farmer$(): harvesting (ripe fruit and crops picked by hand too), planting, breeding.'
             '$(li)Miners level from stone and ores.'),
        text('Side stations pay too:'
             '$(li)$(l)Smith$(): carving bone at the Ossuary, forging at the Mechanical Fusion Anvil.'
             '$(li)$(l)Cook$(): cutting on a cutting board.'
             '$(li)$(l)Hunter$(): catching butterflies, fireflies and the like with a capture net.'),
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
        text('More optional bosses, each with a quest in its chapter:$(li)$(l)Chapter 1$(): the Sandworm, the '
             'Yeti, the Kraken, the Infernal Dragon and the Corrupted Champion$(li)$(l)Chapter 2$(): the '
             'Underworld Knight, the Gauntlet, the Night Lich and the Void Blossom$(li)$(l)Chapter 3$(): the '
             'Obsidilith$(br2)The Field Guide has a page for each one.'),
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
        text('Almost every boss gives each player nearby (64 blocks) their own $(item)trophy$() when it falls. Quests '
             'check for trophies, so the whole group gets credit, not only whoever landed the last hit.'
             '$(br2)Keep them: some raise your world tier.'),
        text('$(li)Amethyst Crab: Geode Claw$(li)Ancient Remnant: Sun-Bleached Fang$(li)Maledictus: '
             'Frostbound Crown$(li)Leviathan: Abyssal Scale$(li)Netherite Monstrosity: Molten Heart'
             '$(li)Ender Guardian: Citadel Keystone$(li)Ender Dragon: Dragonscale$(li)Wither: Ashen Skull '
             'Shard'),
        text('Optional Overworld bosses:$(li)Ferrous Wroughtnaut: Wrought Rivet$(li)Frostmaw: Rimefang Tusk'
             '$(li)Umvuthi: Sunbird Plume$(li)Sandworm: Dune Fang$(li)Yeti: Hoarfrost Pelt$(li)Kraken: Abyssal '
             'Ink$(li)Infernal Dragon: Cinder Scale$(li)Corrupted Champion: Champion\'s Tarnished Crest'),
        text('Optional Nether and End bosses:$(li)Underworld Knight: Oathbreaker Seal$(li)Gauntlet: Gauntlet Core'
             '$(li)Night Lich: Phylactery Shard$(li)Void Blossom: Void Petal$(li)Obsidilith: Obsidian Heartstone'),
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
             'inventory, armor, accessories, backpack and all your experience. Nothing is lost.$(br2)Chat tells you where '
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
    ('key.neoorigins.skill_1', 'Folk ability 1'),
    ('key.neoorigins.skill_2', 'Folk ability 2'),
    ('key.neoorigins.skill_3', 'Folk ability 3'),
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


# Pack 1.5.5 pages (mod audit: the newer mods weren't in the book).
E['professions'] += [
    ('croptopia', 'Cook: Croptopia Kitchen', 'croptopia:cooking_pot', [
        text('Croptopia adds dozens of crops, fruit trees and dishes. Simple dishes (one to three ingredients) are '
             'free for anyone and give a new Cook a little experience. Hearty dishes (four or five) need Cook 10, '
             'grand dishes (six or more) Cook 20.$(br2)Every new dish a Cook makes pays a bonus the first time.'),
        text('Its kitchen tools (the $(item)Stock Pot$(), frying pan, knife, food press) stay in the grid. Dishes '
             'from the Farmer\'s Delight cooking pot are free for everyone.$(br2)Where Croptopia and Farmer\'s '
             'Delight make the same thing (tomatoes, rice, hamburgers...), the pack keeps one: a stray Croptopia '
             'copy turns into it at the crafting table.'),
    ]),
    ('keg', 'Cook: The Keg', 'brewinandchewin:keg', [
        text('A $(item)Keg$() ferments drinks and ages cheese over time. Fill it, wait, and pour.$(br2)Each '
             'drink or cheese a Cook takes from the keg gives Cook experience, and a new one pays the new-dish '
             'bonus.'),
    ]),
    ('foraging', 'Foraging and Wild Things', 'mushroomquest:blue_glowshroom', [
        text('Mushrooms grow on stumps and trunks in the woods: a Hunter levels from foraging them. Many cook '
             'into meals, and some brew into potions.$(br2)Naturalist\'s wild animals drop hides, fur, fat, teeth '
             'and antlers for Hunters. Some of them bite back.'),
        text('A $(item)capture net$() catches butterflies, fireflies and other small creatures, and a Hunter '
             'levels from each catch.$(br2)Farmers level from picking ripe Croptopia crops and fruit by hand.'),
    ]),
]

E['loot'] += [
    ('relics', 'Relics', 'relics_rpgs:jewel_figurine_ruby', [
        text('$(item)Relics$() are trinkets worn in their own slot (accessories, G). They come in four grades: '
             'lesser, medium, greater and superior, each stronger than the last.$(br2)Bosses and dungeons give '
             'them out. A spare relic recycles into rarity materials at the Salvaging Table, more for a higher '
             'grade.'),
    ]),
]

E['home'] = [
    ('storage', 'Storage', 'toms_storage:storage_terminal', [
        text('An $(item)Inventory Connector$() links every chest touching it, and every chest touching those, up '
             'to 16 blocks away. A $(item)Storage Terminal$() next to it shows everything in one window.$(br2)Use '
             '$(l)one$() connector per storage room: two connectors touching the same chests count their items '
             'twice in the terminal (the items are fine; the number is wrong).'),
    ]),
    ('furniture', 'Furniture', 'handcrafted:oak_chair', [
        text('Chairs, tables, shelves, cupboards, beds and plates in every kind of wood: craft them at a '
             'crafting table, no job needed.$(br2)Sit on a chair or bench by using it.'),
    ]),
    ('chisel', 'The Chisel', 'chisel:chisel', [
        text('A $(item)Chisel$() carves stone, wood, glass and more into decorative versions of the same block. '
             'Put blocks in its window (use it in the air) and take the version you want.'),
    ]),
    ('obelisk', 'The Experience Obelisk', 'cognition:experience_obelisk', [
        text('An $(item)Experience Obelisk$() is the party\'s well of experience. Anyone can pour levels in and '
             'draw them out, so the group can feed whoever needs levels to bind spells or enchant.$(br2)It stores '
             'the experience itself, not levels: ten levels poured in at level 40 are worth far more than ten '
             'at level 5.'),
        text('$(l)Making one$()$(li)Cognitive Flux: lapis, an amethyst shard and paper (makes 4).$(li)Smelt it into '
             'Amalgam.$(li)Amalgam with copper: Alloy. Amalgam with an emerald: Crystal.$(li)Alloy, Crystal and '
             'redstone: an Astute Assembly.$(li)Then the obelisk.$(br2)Flux turns up in ruined portals and '
             'Assemblies in desert pyramids.'),
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
     'Its $(item)Molten Heart$() counts for the quest book, and the kill earns an Ascension point.'),
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
    # Pack 1.5.5: Bosses'Rise, Bosses of Mass Destruction and The Graveyard. Optional side quests; their gear
    # always drops with a rarity. Trophies: tools/gen_trophy_icons.py.
    ('sandworm', 'block_factorys_bosses:sandworm', 'Sirok, the Sandworm', 'minerpg:trophy_sandworm',
     {'lair': in_structure('block_factorys_bosses:sandworm_nest')}, 'minerpg:trophy_sandworm',
     'A worm longer than a ship, nesting under the dunes. The sand ripples before it strikes.',
     'It dives and bursts up under whoever stands still. Keep moving, and hit it hard each time it surfaces.',
     'Its spit poisons. Bring milk or a cure.',
     'Its $(item)Dune Fang$() counts for the quest book.'),
    ('yeti', 'block_factorys_bosses:yeti', 'Skor, the Yeti', 'minerpg:trophy_yeti',
     {'lair': in_structure('block_factorys_bosses:yeti_hideout')}, 'minerpg:trophy_yeti',
     'A shaggy giant who has made a cave in the snowy plains his own, and does not share it.',
     'It hurls ice and drives spikes up through the ground. Spread out so one volley never hits the whole party.',
     'Its blows are slow but brutal. Roll them; do not trade hits.',
     'Its $(item)Hoarfrost Pelt$() counts for the quest book.'),
    ('kraken', 'block_factorys_bosses:kraken', 'Nerakyss, the Kraken', 'minerpg:trophy_kraken',
     {'lair': in_structure('block_factorys_bosses:kraken_ship')}, 'minerpg:trophy_kraken',
     'A wrecked ship rides the deep ocean, and something holds it in its arms. Its crew still fights for it.',
     'Its tentacles rise around the deck one after another. Cut them down as they come up, and keep the '
     'cannons off you.',
     'Fight on the ship, not in the water.',
     'Its $(item)Abyssal Ink$() counts for the quest book. Its teeth make the Kraken Trident.'),
    ('infernal_dragon', 'block_factorys_bosses:infernal_dragon', 'Ashlord, the Infernal Dragon',
     'minerpg:trophy_infernal_dragon', {'lair': in_structure('block_factorys_bosses:dragon_tower')},
     'minerpg:trophy_infernal_dragon',
     'A dragon of embers roosting atop a ruined tower, guarded by burning skeletons.',
     'It sets the ground alight and rains fireballs. Clear its guards first, then fight on stone, never in '
     'the flames.',
     'Fire resistance turns this fight around.',
     'Its $(item)Cinder Scale$() counts for the quest book. Its bones make the Dragon Bone armor.'),
    ('corrupted_champion', 'graveyard:lich', 'The Corrupted Champion', 'minerpg:trophy_corrupted_champion',
     {'lair': in_structure('graveyard:altar')}, 'minerpg:trophy_corrupted_champion',
     'A fallen hero bound to an altar among the graves, waiting to be called back.',
     'It fights in three moods and calls the dead to its side. Thin its servants before they surround you.',
     'Its altar calls it. Come rested and ready.',
     'Its $(item)Champion\'s Tarnished Crest$() counts for the quest book.'),
    ('night_lich', 'bosses_of_mass_destruction:lich', 'The Night Lich', 'minerpg:trophy_night_lich',
     {'lair': in_structure('bosses_of_mass_destruction:lich_tower')}, 'minerpg:trophy_night_lich',
     'A sorcerer of the frozen peaks who never died. Its tower answers those who have slain enough of the dead.',
     'Its missiles slow you and its comets fall where you stand. Keep moving, and strike when it lands.',
     'Kill undead near the tower to call it.',
     'Its $(item)Phylactery Shard$() counts for the quest book.'),
    ('void_blossom', 'bosses_of_mass_destruction:void_blossom', 'The Void Blossom', 'minerpg:trophy_void_blossom',
     {'lair': in_structure('bosses_of_mass_destruction:void_blossom')}, 'minerpg:trophy_void_blossom',
     'A flower that grew from nothing, rooted deep below the surface.',
     'Spikes break from the floor and its petals heal it. Watch the ground and keep the pressure on.',
     'It cannot move. Use that.',
     'Its $(item)Void Petal$() counts for the quest book.'),
    ('underworld_knight', 'block_factorys_bosses:underworld_knight', 'Helvar, the Underworld Knight',
     'minerpg:trophy_underworld_knight', {'lair': in_structure('block_factorys_bosses:underworld_arena')},
     'minerpg:trophy_underworld_knight',
     'An oathsworn knight who never left his arena in the Nether. Its gates open only to a key won inside.',
     'He marks one of you and opens rifts. Whoever is marked should keep away while the rest strike.',
     'Find the key before you look for him.',
     'Its $(item)Oathbreaker Seal$() counts for the quest book.'),
    ('gauntlet', 'bosses_of_mass_destruction:gauntlet', 'The Gauntlet', 'minerpg:trophy_gauntlet',
     {'lair': in_structure('bosses_of_mass_destruction:gauntlet_arena')}, 'minerpg:trophy_gauntlet',
     'A giant iron fist that guards an arena of black stone in the Nether.',
     'Its punches explode where they land, and it fires a beam when it opens. Strike the eye while it is open.',
     'Never stand where it is about to punch.',
     'Its $(item)Gauntlet Core$() counts for the quest book.'),
    ('obsidilith', 'bosses_of_mass_destruction:obsidilith', 'The Obsidilith', 'minerpg:trophy_obsidilith',
     {'lair': in_structure('bosses_of_mass_destruction:obsidilith_arena')}, 'minerpg:trophy_obsidilith',
     'A living pillar of obsidian on the outer islands of the End.',
     'It drops anvils, raises pillars and sends waves across the floor. Jump the waves and stay off the '
     'center when it rises.',
     'It hits hardest of all the optional bosses. Bring the whole party.',
     'Its $(item)Obsidian Heartstone$() counts for the quest book.'),
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
