# minerpg class kit: Archer. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.archers.spell_book/archer"}',spell_engine:item_model="archers:item/spell_book/archer",spell_engine:spell_container={pool:"archers:spell_book/archer"}] 1
give @s archers:composite_longbow 1
give @s archers:archer_armor_chest 1
give @s minecraft:arrow 64
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
