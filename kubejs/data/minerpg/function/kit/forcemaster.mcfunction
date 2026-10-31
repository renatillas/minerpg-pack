# minerpg class kit: Forcemaster. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.forcemaster_rpg.spell_book/forcemaster"}',spell_engine:item_model="forcemaster_rpg:item/spell_book/forcemaster",spell_engine:spell_container={pool:"forcemaster_rpg:spell_book/forcemaster"}] 1
give @s forcemaster_rpg:iron_knuckle 1
give @s forcemaster_rpg:oriene_chest 1
tellraw @s {"text": "No blade, no bow, no need. Your fists carry the weight of a storm.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
