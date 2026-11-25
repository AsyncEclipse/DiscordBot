"""Faction-channel reference text, posted to the Faction Reference thread."""
import json
from functools import lru_cache

from helpers import FactionData


@lru_cache(maxsize=2)
def faction_references(community_factions=True):
    references = []

    def send_community_sheet(message, board_file):
        if community_factions:
            references.append((message, board_file))

    with open("data/sectors.json") as sector_file:
        sectors = json.load(sector_file)

    message = "\n".join(["# Eridani Empire",
                         FactionData.starting_sector_line("eri", sectors),
                         "- 2🛡 Draw two random Reputation Tiles before the game starts,"
                         + " and place them facedown on your Reputation Track.",
                         "- -2 🔴 Start with two fewer Influence Discs"
                         + " (leave your two leftmost Influence Track spaces empty).",
                         "- These Ship Blueprints have additional Energy Production:",
                         "  - **Interceptor** - 1⚡",
                         "  - **Cruiser** - 1⚡",
                         "  - **Dreadnought** - 1⚡"])
    references.append((message, "eridani_board.png"))

    message = "\n".join(["# Hydran Progress",
                         FactionData.starting_sector_line("hyd", sectors),
                         "- ⚗️ During game setup, place a Population Cube in the"
                         + " Advanced Science Population Square on your Starting Sector."])
    references.append((message, "hydran_board.png"))

    message = "\n".join(["# Planta",
                         FactionData.starting_sector_line("pla", sectors),
                         "- Your Population Cubes are automatically destroyed by"
                         + " opponent Ships at the end of the Combat Phase.",
                         "- 1 extra VP for each Controlled Sector at the end of the game.",
                         "- All Ship Blueprints have reduced Initiative Bonuses.",
                         "- All Ship Blueprints have additional Computers and Energy Production"
                         + " but have one less Ship Part Space:",
                         "  - **Interceptor**, **Cruiser**, **Dreadnought** - +1⬜ 2⚡",
                         "  - **Starbase** - +1⬜ 5⚡"])
    references.append((message, "planta_board.png"))

    message = "\n".join(["# Descendants of Draco",
                         FactionData.starting_sector_line("dra", sectors),
                         "- __Explore Action__: For each Activation, you may flip"
                         + " two Sectors from which to choose one (or none)to place."
                         + " Unplaced Sectors are discarded faceup in the corresponding Sector Discard Pile.",
                         "- 1 VP per Ancient on the game board at the end of the game.",
                         "- You may have Ships in Sectors containing Ancients"
                         + " but are not allowed to battle the Ancients."
                         + " Your ships are not Pinned by Ancients."
                         + " You may place Influence Discs in Sectors with Ancients;"
                         + " you are not allowed to collect Discovery Tiles from Sectors containing Ancients."])
    references.append((message, "draco_board.png"))

    message = "\n".join(["# Mechanema",
                         FactionData.starting_sector_line("mec", sectors),
                         "- Cheaper Building costs (instead of):",
                         "  - **Interceptor**: 2🔧 (3)",
                         "  - **Cruiser**: 4🔧 (5)",
                         "  - **Dreadnought**: 7🔧 (8)",
                         "  - **Starbase**: 2🔧 (3)",
                         "  - **Orbital**: 3🔧 (4)",
                         "  - **Monolith**: 8🔧 (10)"])
    references.append((message, "mechanema_board.png"))

    message = "\n".join(["# Orion Hegemony",
                         FactionData.starting_sector_line("ori", sectors),
                         "- Start with a Cruiser in your Starting Sector instead of an Interceptor.",
                         "- All Ship Blueprints have increased Initiative Bonuses.",
                         "- These Ship Blueprints have additional Energy Production:",
                         "  - **Interceptor**: 1⚡",
                         "  - **Cruiser**: 2⚡",
                         "  - **Dreadnought**: 3⚡"])
    references.append((message, "orion_board.png"))

    message = "\n".join(["# Wardens of Magellan",
                         FactionData.starting_sector_line("mag", sectors),
                         "- Start with a Discovery Tile facedown on the Discovery Tile Symbol"
                         + " on the top Tech Track of your Species Board.",
                         "- Resolve the Discovery Tile on your Species Board the first time"
                         + " you place a fourth Tech on one of your Tech Tracks."
                         + " If the Discovery Tile allows you to place something in a Sector"
                         + " (such as Ancient Cruiser or Ancient Orbital), place it in your Starting Sector."
                         + " If you do not control your Starting Sector, you must take the tile as 2VP.",
                         "- 1 VP at the end of the game per Discovery Tile you used as a Ship Part.",
                         "- At any time, you may flip unused Colony Ships to gain"
                         + " one Resource of your choice per Colony Ship flipped."
                         + " (Note: only refresh 1 colony ship with the influence action)"])
    references.append((message, "magellan_board.png"))
    message = "\n".join(["# Enlightened of Lyra",
                         FactionData.starting_sector_line("lyr", sectors),
                         "- 1 VP per Shrine\\* you control at the end of the game.",
                         "- During the Combat Phase, you may flip unused Colony Ships"
                         + " to reroll one of your own dice per Colony Ship flipped.",
                         "## - \\*Shrines",
                         "- You start the game with nine Shrines (special Structures)"
                         + " on the indicated spaces of your Shrine Board])",
                         "- With each **Research** Action, you may additionally place "
                         + "one Shrine from your Shrine Board"
                         + " in any Sector you Control by paying its indicated cost"
                         + " and adhering to the following restrictions:",
                         "  - Shrines must be placed next to a planet of the same color"
                         + " as the Resource used to place the Shrine (or a gray planet).",
                         "  - Each planet may have only one Shrine.",
                         "- Shrines cannot be placed using the **Build** Action.",
                         "- When you place the last Shrine from a row of the Shrine Board,"
                         + " gain the indicated bonus:",
                         "  - __Wormhole Generator ability__: You may Explore, Move to, and Influence "
                         + "adjacent Sectors if the edges connecting the Sectors contain one Wormhole.",
                         "  - __Discovery Tile__: If the Discovery Tile allows you to place something in a Sector"
                         + " (such as Ancient Cruiser or Ancient Orbital), place it in your Starting Sector."
                         + " If you do not control your Starting Sector, you must take the tile as 2VP.",
                         "  - __Extra Influence Disc__: You receive one additional Influence Disc,"
                         + " placed immediately on your Influence Track"
                         + " (you start with 4 extra Influence Discs in your Species Tray instead of 3)."])
    references.append((message, "lyra_board.png"))
    message = "\n".join(["# The Exiles",
                         FactionData.starting_sector_line("exl", sectors),
                         "- Start with an Orbital in your Starting Sector.",
                         "- 1 VP for each Orbital with your Population Cube at the end of the game.",
                         "- Orbitals with your Population Cubes are considered Ships:",
                         "  - They have their own Blueprints but are unable to receive Drive Ship Part Tiles",
                         "  - When destroyed in battle, return your Population Cube to the"
                         + " Science or Money Graveyard, but do not remove the Orbital miniature.",
                         "  - our destroyed Orbitals each add 1 to your opponent’s Reputation Tile draw (max 5).",
                         "- You cannot construct Starbases.",
                         "- Your Orbitals have Ship Blueprints."])
    references.append((message, "exile_board.png"))

    message = "\n".join(["# Rho Indi Syndicate",
                         FactionData.starting_sector_line("rho", sectors),
                         "- Start with two Interceptors in your Starting Sector.",
                         "- You have only two Ambassador Tiles.",
                         "- After drawing Reputation Tiles, gain Money equal to"
                         + " the number of Reputation Tiles you drew minus 1.",
                         "- You do not lose VP for holding the Traitor Card at the end of the game.",
                         "- You cannot construct Dreadnoughts.",
                         "- Increased Building costs (instead of):",
                         "  - **Interceptor**: 4🔧 (3)",
                         "  - **Cruiser**: 6🔧 (5)",
                         "  - **Starbase**: 4🔧 (3)",
                         "- Interceptor and Cruiser Ship Blueprints have increased Initiative Bonuses.",
                         "- All Ship Blueprints have additional **Gauss Shields**:",
                         "  - **Interceptor**: -1⬛",
                         "  - **Cruiser**: -1⬛",
                         "  - **Dreadnought**: -1⬛"])
    references.append((message, "rho_board.png"))

    message = "\n".join(["# Terrans",
                         FactionData.starting_sector_line("ter2", sectors)])
    references.append((message, "terran_conglomerate_board.png"))

    message = "\n".join(["# Atlantians",
                         FactionData.starting_sector_line("atl", sectors),
                         "- Start with Ancient Labs in the Nano Tech track.",
                         "- **Ancient Spirit:** Draw two discovery tiles and choose one to resolve. "
                         "Replace any +6 Materials or Ancient Cruiser tile with another draw.",
                         "- **Ancient Instinct:** After a Research action, you may perform Upgrade 1 "
                         "using a technology researched during that action.",
                         "- **Ancient Power:** Gain 1 VP for each discovery tile installed on a Ship Blueprint.",
                         "- **Price of Power:** Each ship costs 1 additional Materials for each discovery tile "
                         "beyond the first installed on its Ship Blueprint."])
    send_community_sheet(message, "atlantians_board.png")

    message = "\n".join(["# Remnants of Ra",
                         FactionData.starting_sector_line("ra", sectors),
                         "- Start with Plasma Cannon in the Military Tech track.",
                         "- **Power of the Ancients:** An additional population cube of any type in a sector"
                         " with an artifact key (placed on top of the influence disk)."
                         " This includes your home sector.",
                         "- **Secrets of the Ancients:** Gain 1 additional VP for each sector you control"
                         " with an artifact key.",
                         "- You flip only 1 colony ship per Influence action."])
    send_community_sheet(message, "ra_board.png")

    message = "\n".join(["# Techno-Mages",
                         FactionData.starting_sector_line("tm", sectors),
                         "- Start with no technologies. You may spend part of your initial science to buy"
                         " 1 technology before the game begins if you wish.",
                         "- **Technology finds a Way:** Use 2 Colony Ships to place a resource cube of the"
                         " correct type on an Advanced planet you could not normally populate.",
                         "- **Techno-Magic:** At the start of each combat, you may temporarily Upgrade 1 on"
                         " each ship blueprint. Place the new part upside down so that you remember to"
                         " remove it after the battle. You may not remove ship parts and you cannot place"
                         " Ancient ship parts. Normal power restrictions apply. Where timing matters"
                         " (e.g. vs Spiral), the Defender chooses last.",
                         "- **Limited Manufacturing:** You only get 1 Activation with a Build Action, and you"
                         " may only flip 1 Colony Ship with an Influence action."])
    send_community_sheet(message, "tm_board.png")

    message = "\n".join(["# The Wulfen",
                         FactionData.starting_sector_line("wul", sectors),
                         "- **Spine Cannons:** Each ship has two dedicated Spine Cannon slots. The"
                         " Cannon Slot fires normally; the Augment Slot's weapon does not fire, but"
                         " before firing each turn choose +X to Hit or +X Damage, where X is that"
                         " weapon's damage. Spine slots hold guns only (no Missiles or Rift weapons).",
                         "- **Wolf Pack:** 3 Move activations. Anytime you roll a 6, convert a miss from"
                         " the same attack pool into a Hit, or save a reroll for a ship firing later"
                         " in the round.",
                         "- No Interceptors. Cruisers: 6 maximum, one fewer ship part slot, cost 4.",
                         "- Start with 3 Money / 3 Science / 2 Materials and a Cruiser instead of an"
                         " Interceptor.",
                         "- Start with Fusion Source in the Grid tech track.",
                         "- 5 reputation slots (2 can hold ambassadors).",
                         "- Home sector Lupis (252)."])
    send_community_sheet(message, "wulfen_board.png")

    message = "\n".join(["# Turtugan",
                         FactionData.starting_sector_line("tur", sectors),
                         "- **Deep Space Explorers:** Keep 2 extra S3 sectors in a separate hidden stack."
                         " When exploring an outer-sector position, you may draw the next tile from"
                         " this reserve instead of the normal stack, even if the normal stack is empty.",
                         "- **Harvesters:** Starbases are Harvesters. They can move 1 activation per Explore"
                         " action and may be placed over an unsettled planet in their sector at the end of"
                         " any Turn. During Production, they generate 1 resource of any type that planet"
                         " produces, even on Advanced Planets you cannot populate. Harvesters cannot remove"
                         " their Drive.",
                         "- **Carapace Shields:** At the start of any combat or engagement round you may"
                         " engage or disengage Carapace Shields for any class of ship in the battle."
                         " Once engaged, that ship gets the following: -1 Damage from all its weapons"
                         " (Min = 0); -1 Damage from all successful attacks against it (Min=1)."
                         " Missiles may instead get -1 to Hit (attacker's choice).",
                         "- Start with a Harvester (Starbase) instead of an Interceptor.",
                         "- Modified ship designs: Slower, offboard Hull & Computer.",
                         "- Initial Technology: Starbase.",
                         "- Home sector Turtuga: the print numbers it 252; the bot uses 253 because"
                         " 252 is Lupis."])
    send_community_sheet(message, "turtugan_board.png")

    message = "\n".join(["# Kurita Prefecture",
                         FactionData.starting_sector_line("kur", sectors),
                         "- Start with Phase Shields, 3 Colony Ships, and 2 Money / 3 Science / 4 Materials.",
                         "- **Honour your enemy with the first shot:** Your opponents take their missile round"
                         " & first engagement round BEFORE you shoot. Then you take your missile round &"
                         " first engagement round. From the 2nd engagement round onwards normal speed rules apply.",
                         "- **Honour the Victorious, Fight to the Death:**",
                         "  - +1 to Battle Rep score for winning battles"
                         " (a 2-value tile is 3 VP if you win, 1 if you lost). Place a Dmg Cube next to the"
                         " Battle Rep tile if it was a win.",
                         "  - -1 to Battle Rep score for losing battles.",
                         "  - If you retreat any ship you do not draw Battle Reputation at all, regardless of"
                         " ships destroyed.",
                         "  - The Traitor card is worth -4 VPs.",
                         "- **Elite Warriors:** +1 to Hit off-board on all ships.",
                         "- **Ships:** Starbases have an extra Hull.",
                         "- Standard trade (3:1). Home system Edo (#251)."])
    send_community_sheet(message, "kurita_board.png")

    message = "\n".join(["# Heralds of Ragnarok",
                         FactionData.starting_sector_line("her", sectors),
                         "- Start with Neutron Bombs in the Military Tech track.",
                         "- Start with a Cruiser in your starting sector instead of an Interceptor.",
                         "- **Raid:** Move actions include a build activation.",
                         "- **Regroup:** Build actions include a move activation.",
                         "- **Interceptor:** Cost 4 Materials instead of 3. One additional blueprint slot"
                         " containing a Hull. Initiative bonus 1 instead of 2.",
                         "- **Cruiser:** Cost 4 Materials instead of 5. One less Hull blueprint slot."
                         " Initiative bonus 2 instead of 1.",
                         "- 5 reputation slots: 1 ambassador-only, 2 mixed, 2 reputation-only."])
    send_community_sheet(message, "heralds_board.png")

    message = "\n".join(["# The Wraith",
                         FactionData.starting_sector_line("wra", sectors),
                         "- Start with **Phase Module** in the Military Tech track.",
                         "- **Phase Technology:** You may swap subsequent Build activations for Upgrade"
                         " activations during any Build Action (you may swap all but the first).",
                         "- **Ghosts:** The Wraith may retreat immediately when it is their turn to fire"
                         " (there is no extra round of shooting).",
                         "- **Soul-Hunters:** Wraith capture the souls of planets they attack. To use Neutron Bombs"
                         " you must research and have 2 available blueprint Power using the Phase Module. You get +1 offboard"
                         " power and +1 VP per sector you destroy with enemy population cubes in it (increment"
                         " the Dice on your faction board). It does not matter if you do not settle the sector"
                         " or lose it later. Offboard power permanently adds energy to every blueprint, including"
                         " for upgrades, and is never consumed.",
                         "- **Phase Module:** This is built into all your ships, and you use it for a range of"
                         " benefits, limited by how much Power you have: **Always:** Cloaking Device;"
                         " **for 1 Power each:** +1 to Hit, +1 Shield; **for 2 Power:** Neutron Bombs if"
                         " researched, +2 Initiative; **for 3 Power:** Ignore Shields. Declare options at the"
                         " start of each combat per blueprint.",
                         "- **Ships:** +1 Cost, Phase Module. The card prints 1 Diplomat; the board"
                         " prints 1 INF activation and 2 colony ships flipped per Influence action.",
                         "- The board prints home sector 225; the bot uses the free sector 254"
                         " (226 is the Planta home)."])
    send_community_sheet(message, "wraith_board.png")

    message = "\n".join(["# Children of Cog",
                         FactionData.starting_sector_line("cog", sectors),
                         "- Start with Nanorobots in the Nano Tech track.",
                         "- **Mechanical Mind:** Alternative tech board, prioritising breadth over depth.",
                         "- **Infinite Possibilities:** Upgrade 3. Gain an additional upgrade activation as the"
                         " first or last activation when you perform a Build or Move action.",
                         "- **Adaptive Transformation:** Using an upgrade activation, replace two Interceptors"
                         " with a Cruiser gaining 1 Material; or two Cruisers with a Dreadnought gaining"
                         " 2 Materials. Using an upgrade activation and 1 Material, replace a Cruiser with two"
                         " Interceptors; or for 2 Materials replace a Dreadnought with two Cruisers. All ships"
                         " must be in the same sector.",
                         "- The board prints home sector 254; the bot uses the free sector 256"
                         " (254 is the Wraith home)."])
    send_community_sheet(message, "cog_board.png")

    message = "\n".join(["# Legion of Midas",
                         FactionData.starting_sector_line("mid", sectors),
                         "- Start with Advanced Economy in the Grid Tech track.",
                         "- **Midas Touch:** Before you perform an action, you can spend money to perform an"
                         " additional activation of the same type: Explore 4, Research 3, Upgrade 1, Build 1,"
                         " Move 1, Influence 1 (an additional action disk). With 7 or fewer action disks left,"
                         " each cost is 1 higher.",
                         "- **Money is Power:** During game setup, place a Population Cube in the Advanced"
                         " Money Population Square on your Starting Sector.",
                         "- **All That Glitters:** Midas earn 1 Money instead of 2 when passing first."])
    send_community_sheet(message, "midas_board.png")

    message = "\n".join(["# The Horde",
                         FactionData.starting_sector_line("hor", sectors),
                         "- Start with Neutron Bombs in the Military Tech track and Nanorobots in the Nano"
                         " Tech track.",
                         "- **Built for War:** +1 damage when you hit with an unmodified 6. Does not apply to"
                         " Rift weapons.",
                         "- **Reduced Initiative:** Interceptors, Cruisers and Starbases have 1 less initiative.",
                         "- **Raid:** Move actions include a Build activation.",
                         "- **Call To Arms:** Gain Materials when your ships are destroyed in a sector you do"
                         " not control: Interceptor 1, Cruiser 2, Dreadnought 3.",
                         "- **Battle Focus:** Upgrade activations must be spent on different ship classes.",
                         "- **Alternative Tech Board:** 4 slots per track, with discounts -1, -3, -5.",
                         "- Home sector 288"
                         " (Kassus Gar Rift)."])
    send_community_sheet(message, "horde_board.png")

    message = "\n".join(["# Vorlons",
                         FactionData.starting_sector_line("vor", sectors),
                         "- Start with Regenerative Hull in the Nano Tech track.",
                         "- **Tech Masters:** For an increased Science cost, you may put a Tech in the wrong"
                         " Tech Tray. The extra cost is 2 the first time, then 1 more each subsequent time"
                         " (3 the second, 4 the third). This extra cost cannot be reduced by discounts.",
                         "- **Organic Tech:** Whenever you research a new Tech, you may have 1 free Upgrade"
                         " activation for that Tech only.",
                         "- **Few in Number:** Only flip back 1 Colony Ship on an Influence action.",
                         "- **Regenerative Hull:** All ships start with it. Heal does not work against Ancients,"
                         " but does against Guardians and the GCDS.",
                         "- **Research Discounts are all 1 more.**",
                         "- **Centre Bonus:** 2 VP if you or an Ally control the Centre.",
                         "- Trade 4:1. Four reputation slots."])
    send_community_sheet(message, "vorlons_board.png")

    message = "\n".join(["# Hegemony of the Highest Cushion",
                         FactionData.starting_sector_line("heg", sectors),
                         "- Start with Fusion Drive in the Nano Tech track.",
                         "- **Nine Lives:** You may flip a Colony Ship to make an attacker reroll a Damage dice.",
                         "- **Pounce:** +1 to Hit in the first engagement round (not the Missile round) if you shoot first.",
                         "- **Solitary Hunter:** +1 Initiative and +1 to Hit if there is only 1 Hegemony ship in the battle"
                         " (attacking or defending).",
                         "- **Pride:** +2 Bonus VPs if you control the Centre at the end of the game.",
                         "- Start with 2 Materials / 3 Science / 3 Money, 3 Colony Ships,"
                         " standard ships and standard trade (3:1). Four reputation slots.",
                         "- Home system The Cattery (#276)."])
    send_community_sheet(message, "hegemony_board.png")

    return references
