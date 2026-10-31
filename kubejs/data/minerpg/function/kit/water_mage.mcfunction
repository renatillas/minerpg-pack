# minerpg class kit: Water Mage. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.elemental_wizards_rpg.spell_book/aqua"}',spell_engine:item_model="elemental_wizards_rpg:item/spell_book/aqua",spell_engine:spell_container={pool:"elemental_wizards_rpg:spell_book/aqua"}] 1
give @s elemental_wizards_rpg:wand_aqua 1
give @s elemental_wizards_rpg:elemental_chest 1
give @s mrpg_lib:aqua_stone 32
advancement grant @s only minerpg:calling/water_mage/start
tellraw @s {"text": "The tide answers to you. Push your foes back and wash your friends clean.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
