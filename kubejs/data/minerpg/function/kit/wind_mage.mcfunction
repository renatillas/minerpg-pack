# minerpg class kit: Wind Mage. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.elemental_wizards_rpg.spell_book/wind"}',spell_engine:item_model="elemental_wizards_rpg:item/spell_book/wind",spell_engine:spell_container={pool:"elemental_wizards_rpg:spell_book/wind"}] 1
give @s elemental_wizards_rpg:wand_wind 1
give @s elemental_wizards_rpg:elemental_chest 1
give @s mrpg_lib:storm_stone 32
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
