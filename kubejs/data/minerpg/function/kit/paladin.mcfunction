# minerpg class kit: Paladin. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.paladins.spell_book/paladin"}',spell_engine:item_model="paladins:item/spell_book/paladin",spell_engine:spell_container={pool:"paladins:spell_book/paladin"}] 1
give @s paladins:iron_mace 1
give @s paladins:paladin_armor_chest 1
give @s runes:healing_stone 32
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
