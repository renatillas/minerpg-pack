# minerpg class kit: Arcane Wizard. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.wizards.spell_book/arcane"}',spell_engine:item_model="wizards:item/spell_book/arcane",spell_engine:spell_container={pool:"wizards:spell_book/arcane"}] 1
give @s wizards:wand_arcane 1
give @s wizards:wizard_robe_chest 1
give @s runes:arcane_stone 32
tellraw @s {"text": "You bend raw magic into shape. Keep your distance and let the arcane do the talking.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
