# minerpg class kit: War Archer. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.archers_expansion.spell_book/war_archer"}',spell_engine:item_model="archers_expansion:item/spell_book/war_archer",spell_engine:spell_container={pool:"archers_expansion:spell_book/war_archer"}] 1
give @s archers:rapid_crossbow 1
give @s archers_expansion:war_archer_chest 1
give @s minecraft:arrow 64
tellraw @s {"text": "A crossbow, a steady hand and a hail of bolts. Hold the line from range.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
