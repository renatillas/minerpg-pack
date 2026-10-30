# minerpg class kit: Fire Wizard. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.wizards.spell_book/fire"}',spell_engine:item_model="wizards:item/spell_book/fire",spell_engine:spell_container={pool:"wizards:spell_book/fire"}] 1
give @s wizards:wand_fire 1
give @s wizards:wizard_robe_chest 1
give @s runes:fire_stone 32
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
