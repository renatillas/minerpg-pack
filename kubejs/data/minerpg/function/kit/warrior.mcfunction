# minerpg class kit: Warrior. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.rogues.spell_book/warrior"}',spell_engine:item_model="rogues:item/spell_book/warrior",spell_engine:spell_container={pool:"rogues:spell_book/warrior"}] 1
give @s rogues:iron_double_axe 1
give @s rogues:warrior_armor_chest 1
advancement grant @s only minerpg:calling/warrior/start
tellraw @s {"text": "You go in first and come out last. Swing wide and let them come to you.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
