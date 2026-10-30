# minerpg: put the player on the highest Apotheosis world tier they have unlocked.
# Every apotheosis:progression/<tier> advancement runs this as its reward (overrides in
# kubejs/data/apotheosis/advancement/progression/), and the "Welcome, Traveler" quest runs it too.
# The checks go from the top tier down and stop at the first match ("return run"), so the
# tier only ever rises: unlocking a lower tier late (e.g. a Geode Claw picked up after the
# Nether Sigil) never lowers it. Manual tier changes are off in config/apotheosis/apotheosis.cfg.
execute if entity @s[advancements={apotheosis:progression/pinnacle=true}] run return run apoth set_world_tier @s pinnacle
execute if entity @s[advancements={apotheosis:progression/summit=true}] run return run apoth set_world_tier @s summit
execute if entity @s[advancements={apotheosis:progression/ascent=true}] run return run apoth set_world_tier @s ascent
execute if entity @s[advancements={apotheosis:progression/frontier=true}] run return run apoth set_world_tier @s frontier
apoth set_world_tier @s haven
