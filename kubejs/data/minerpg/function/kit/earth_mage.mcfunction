# minerpg class kit: Earth Mage. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.elemental_wizards_rpg.spell_book/terra"}',spell_engine:item_model="elemental_wizards_rpg:item/spell_book/terra",spell_engine:spell_container={pool:"elemental_wizards_rpg:spell_book/terra"}] 1
give @s elemental_wizards_rpg:wand_terra 1
give @s elemental_wizards_rpg:elemental_chest 1
give @s mrpg_lib:terra_stone 32
advancement grant @s only minerpg:calling/earth_mage/start
tellraw @s {"text": "Stone listens when you speak. Stand your ground, and the ground stands with you.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
