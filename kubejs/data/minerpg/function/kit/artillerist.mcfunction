# minerpg class kit: Artillerist. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.artificers.spell_book/artillerist"}',spell_engine:item_model="artificers:item/spell_book/artillerist",spell_engine:spell_container={pool:"artificers:spell_book/artillerist"}] 1
give @s artificers:flintlock 1
give @s artificers:peasant_chest 1
give @s runes:fire_stone 64
give @s minecraft:arrow 64
tellraw @s {"text": "Mortars, mines and a steady flintlock. Pick the ground, and let the fight come to you.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
