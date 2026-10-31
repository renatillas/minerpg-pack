# minerpg class kit: Rogue. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.rogues.spell_book/rogue"}',spell_engine:item_model="rogues:item/spell_book/rogue",spell_engine:spell_container={pool:"rogues:spell_book/rogue"}] 1
give @s rogues:iron_dagger 1
give @s rogues:rogue_armor_chest 1
advancement grant @s only minerpg:calling/rogue/start
tellraw @s {"text": "The first blow is the one that counts. Strike from the shadows and leave before they turn.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
