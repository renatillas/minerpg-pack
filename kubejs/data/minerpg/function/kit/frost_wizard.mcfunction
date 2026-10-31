# minerpg class kit: Frost Wizard. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.wizards.spell_book/frost"}',spell_engine:item_model="wizards:item/spell_book/frost",spell_engine:spell_container={pool:"wizards:spell_book/frost"}] 1
give @s wizards:wand_frost 1
give @s wizards:wizard_robe_chest 1
give @s runes:frost_stone 32
tellraw @s {"text": "Slow them, then shatter them. Nothing reaches you through the ice.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
