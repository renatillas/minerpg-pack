# minerpg class kit: Bard. Run by the "Choose your calling" quest reward (as the player).
give @s spell_engine:spell_book[minecraft:item_name='{"translate": "item.bards_rpg.spell_book/bard"}',spell_engine:item_model="bards_rpg:item/spell_book/bard",spell_engine:spell_container={pool:"bards_rpg:spell_book/bard"}] 1
give @s bards_rpg:wooden_lute 1
give @s bards_rpg:entertainer_garb_chest 1
advancement grant @s only minerpg:calling/bard/start
tellraw @s {"text": "Your song carries the party. Play them stronger, and let the rhythm cut down the rest.", "color": "gray", "italic": true}
tellraw @s {"text":"Your calling answers. Wear the tome in its slot and hold your weapon.","color":"gold"}
