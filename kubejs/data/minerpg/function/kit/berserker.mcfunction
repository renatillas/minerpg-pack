# minerpg class kit: Berserker. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.berserker_rpg.spell_book/berserker"}',spell_engine:item_model="berserker_rpg:item/spell_book/berserker",spell_engine:spell_container={pool:"berserker_rpg:spell_book/berserker"}] 1
give @s berserker_rpg:iron_berserker_axe 1
give @s berserker_rpg:wildling_chest 1
tellraw @s {"text": "Every blow feeds your fury. Get close, stay close, and do not stop.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
