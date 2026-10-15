# Adding a community faction

Checklist from adding the Atlantians, then Remnants of Ra. Faction-specific rules
(abilities) belong in this doc: for the Atlantians the doc originally excluded them and
that was the most expensive gap. Each ability entry must name the existing flow it reuses.

## Shared checklist

- **Faction data:** Add an entry in `data/factions.json`: starting resources, population, technologies, action limits, tracks, ship costs, stock and blueprints. Match the existing fields.
- **Home sector:** Add the home tile in `data/sectors.json`, point `home_planet` to it, and add `images/resources/hexes/<id>.png`. Set population, wormholes and the coordinates used to draw pieces on the tile.
- **Selection:** In `Buttons/Draft.py`, add the faction to `communityFactions` so it appears only when `community_factions` is enabled and neither causes nor receives colour blocks (drafted factions and explicit bans still apply), and give it a display colour in `getColor`. Add it to the setup command's faction choices in `commands/setup_commands.py`. Expose `community_factions: bool = False` during game creation and save it through `setup/GameInit.py`.
- **Colours:** New colours are not supported for now; each new faction must prefer one of the existing setup colours: blue, red, green, yellow, purple, white, pink, brown or teal. A community faction may appear next to a standard faction that shares its colour, and setup hands it another free colour when its preferred one is already taken, so no two players look alike.
- **Name lookups:** Map the full name to the artwork key in both `GamestateHelper.getShortFactionNameFromFull` and `get_short_faction_name`, and in `DrawHelper.get_short_faction_name`. The data/command key and the artwork key may differ (Atlantians: `atl` vs `atlantians`); Remnants of Ra uses `ra` for both.
- **Artwork:** Under `images/resources/components/`, add `factions/<key>_{board,info,ambassador}.png`, `layouts/factionImages/<key>_image.png` (from the faction icon), `layouts/faction_titles/name_trade_<key>.png`, and `layouts/blueprints/classes/<key>_{interceptor,cruiser,dreadnought,starbase}_class.png`. Send the board and reference from `commands/setup_commands.py`. In `DrawHelper.faction_portrait`, return the dedicated `factionImages/<key>_image.png` instead of the crop used for existing faction boards.
- **Checks:** Cover draft visibility and reference files, setup through a first round and artwork paths, and the abilities. These tests check file loading, not visual quality; inspect the rendered board, portraits, blueprints and home tile too.

## Atlantians (`atl`, artwork `atlantians`)

- **Reputation slots:** The first two slots hold reputation only. `Buttons/Reputation.py` fills empty `rep` slots as well as `mixed` slots; `PlayerHelper.is_reputation_only_slot` identifies the two by position (once filled both hold numbers). Diplomacy and minor species in `GamestateHelper.py` preserve them; `DrawHelper.py` draws the rep-only slot background.
- **Ancient Spirit** (two discovery tiles, one chosen; +6 Materials and Ancient Cruiser tiles replaced): reuses the discovery-tile flow — `DiscoveryTileButtons.drawAtlantiansDiscoveryChoices` pops from the shared deck, and the chosen tile continues through the existing `sendDiscoveryTileOptions` / `usedDiscForAbility` path.
- **Ancient Instinct** (Upgrade 1 with the technology just researched): reuses the discovery-tile upgrade path — `ResearchButtons.offerAncientInstinctUpgrade` offers the ship menu and `UpgradeButtons` installs the part for free (no influence disc, no upgrade counter).
- **Ancient Power** (1 VP per discovery tile installed on a blueprint): `DrawHelper.get_public_points` adds `PlayerHelper.installed_discovery_part_count`.
- **Price of Power** (ships cost 1 extra Materials per installed discovery tile beyond the first): `PlayerHelper.get_ship_cost` is the single cost path used by Build, blueprints and ShipHelper.
- Tests: `tests/test_atlantians_*`, `tests/test_ancient_*`, `tests/test_discovery_part_power.py`.

## Remnants of Ra (`ra`, artwork `ra`)

Card (`community-races/factions/Remnants of Ra/ra_info.png`, v1.6) and board both read
verbatim; the source images are the only rules text for this faction.

- **Faction data:** `ra` in `data/factions.json`: 3 Materials, 3 Science, 2 Money, 3 colony ships, Plasma Cannon (`plc`) in `military_tech`, activations 1/1/2/2/2/2, trade value 4, 12 influence discs, standard tracks/ship costs/stock/blueprints, 4 `mixed` reputation slots (the board prints no reputation-only slot).
- **Home sector:** `255` "Osiris Seth" (the number printed on the artwork; 266 was taken by Atlantia). 3 VP, artifact key, one normal money square, one advanced material square, one advanced science square, wormholes `[0,1,3,4]`. `images/resources/hexes/255.png` is `ra_home.jpg` cropped `(0,77,1118,1053)` and resized to 1024x890 (the same recipe as Atlantia).
- **Power of the Ancients** (an additional population cube of any type in a sector with an artifact key, on top of the influence disc, including the home sector): a new `disc_pop` tile field holds the cube, drawn at the influence disc position. Placement asks for the type (money/science/material), takes the cube from that population track (income rises as for any placement) and costs no colony ship. Reuses the population-cube bookkeeping (`*_pop_cubes`) and, on removal, the neutral-cube path in `GamestateHelper.remove_pop` / `PlayerHelper` upkeep, so the player picks which track the cube returns to (the cube's type is not remembered, as for neutral squares). `PopulationButtons.findFullPopulation` lists it so losing the sector, combat population hits and elimination clean it up.
- **Secrets of the Ancients** (1 additional VP per controlled sector with an artifact key): `DrawHelper.get_public_points` adds 1 inside the existing owned-tile loop, like Planta's per-sector point.
- **Influence action flips 1 colony ship instead of 2** (printed above INF on the board and as "1 Colony Ship" on the card): reuses the Magellan branch in `Buttons/Influence.py` (`startInfluence` label and `refreshPopShips`).
- Tests: `tests/test_ra_faction_data.py`, `tests/test_ra_home_sector.py`, `tests/test_ra_faction_setup.py`, `tests/test_ra_artwork.py`, `tests/test_ra_abilities.py`, `tests/test_ra_first_round.py`.

### Risk hypotheses (targeting for probes and verification)

- The disc cube touches the shared population-removal paths (control lost by influence, combat hits, elimination, upkeep graveYard): a cube on an artifact sector must return to a track and never leak into another faction's state.
- The type prompt is an answer-style prompt: a queued second press must not place two cubes (see the `ANSWER_BUTTONS` guard in `ButtonListener.py`).
- `get_public_points` is shared by every faction: the artifact VP must not change existing factions' scores when artifact sectors exist on the board.
- The 1-colony-ship branch in `Influence.py` is shared with Magellan and everyone else; only Remnants of Ra and Magellan may flip 1.
- Setup runs two community-faction setup hooks (Atlantians nano-tech discovery tile, Remnants of Ra home cube) in `Draft.generalSetup`; both must survive a game that drafts both.
