# minerpg class kit: Witcher (Blade). Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.witcher_rpg.spell_book/fencing"}',spell_engine:item_model="witcher_rpg:item/spell_book/fencing",spell_engine:spell_container={pool:"witcher_rpg:spell_book/fencing"}] 1
give @s witcher_rpg:iron_witcher_sword 1
give @s witcher_rpg:witcher_chest 1
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
