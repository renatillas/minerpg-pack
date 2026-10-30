# minerpg class kit: Deadeye. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.archers_expansion.spell_book/deadeye"}',spell_engine:item_model="archers_expansion:item/spell_book/deadeye",spell_engine:spell_container={pool:"archers_expansion:spell_book/deadeye"}] 1
give @s minecraft:bow 1
give @s archers_expansion:deadeye_chest 1
give @s minecraft:arrow 64
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
