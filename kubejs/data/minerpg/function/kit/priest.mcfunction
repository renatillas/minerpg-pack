# minerpg class kit: Priest. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.paladins.spell_book/priest"}',spell_engine:item_model="paladins:item/spell_book/priest",spell_engine:spell_container={pool:"paladins:spell_book/priest"}] 1
give @s paladins:holy_wand 1
give @s paladins:priest_robe_chest 1
give @s runes:healing_stone 32
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
