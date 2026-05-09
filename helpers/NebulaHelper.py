"""Helpers for Nebula sectors (Galactic Events expansion).

A Nebula sector is a hex tile divided into three Subsectors (A/B/C) connected by
internal wormhole connections. Subsectors are exposed as first-class entries in
``gamestate["board"]`` using synthetic position keys ``<parent>A``, ``<parent>B``,
``<parent>C``. The parent position is also retained as a render anchor and is
flagged with ``is_nebula_parent: True``.

See the rulebook (Galactic Events, page 4) for full rules; this module only
provides scaffolding helpers used by Explore / Move / Influence / DrawHelper /
combat upkeep.
"""

import copy


# Sector IDs in data/sectors.json that are nebulas. Currently NGC 5189 and NGC 1952.
NEBULA_SECTOR_IDS = {"295", "395"}

SUBSECTOR_LETTERS = ["A", "B", "C"]

# External hex edges per subsector (using the existing 0..5 edge convention,
# which is N, NE, SE, S, SW, NW).
EXTERNAL_EDGES_BY_SUBSECTOR = {
    "A": [5, 0],   # top: NW + N
    "B": [1, 2],   # right: NE + SE
    "C": [3, 4],   # bottom-left: S + SW
}

# Symbol distribution per subsector. Same layout for both 295 and 395 as a
# baseline. If individual sectors should differ in the future this can be
# parameterised by sector id.
DISC_SUBSECTORS = {"A", "C"}
ANCIENT_SUBSECTOR = "B"

# Subsector centres (relative to a 1024x887 hex image), used as the default
# *_snap coordinates for ship placement. The renderer applies its own per-ship
# offsets (cru/drd y -30, sb y -30) so we don't pre-bake those.
SUBSECTOR_CENTERS = {
    "A": (512, 220),
    "B": (730, 580),
    "C": (294, 580),
}


def is_nebula_subsector(pos):
    """Return True if pos looks like a nebula subsector key (e.g. ``"207A"``)."""
    if not isinstance(pos, str) or len(pos) < 2:
        return False
    letter = pos[-1]
    if letter not in SUBSECTOR_LETTERS:
        return False
    prefix = pos[:-1]
    return prefix.isdigit()


def get_parent_position(pos):
    """Strip a trailing A/B/C from a subsector key. Returns pos unchanged if it
    isn't a subsector key."""
    if is_nebula_subsector(pos):
        return pos[:-1]
    return pos


def get_subsector_letter(pos):
    """Return the trailing A/B/C letter, or None if pos is not a subsector."""
    if is_nebula_subsector(pos):
        return pos[-1]
    return None


def subsectors_of(parent_pos):
    """Return the three subsector keys for a parent position."""
    return [f"{parent_pos}{L}" for L in SUBSECTOR_LETTERS]


def is_nebula_parent(tile_record):
    """True if a board record is a nebula parent anchor (no ships / no influence)."""
    if not isinstance(tile_record, dict):
        return False
    return bool(tile_record.get("is_nebula_parent"))


def is_nebula_position(game, pos):
    """True if ``pos`` (parent or subsector) belongs to a nebula in the gamestate."""
    board = game.gamestate.get("board", {})
    if pos not in board and not is_nebula_subsector(pos):
        return False
    if is_nebula_subsector(pos):
        parent = get_parent_position(pos)
        rec = board.get(parent)
        return is_nebula_parent(rec) if rec else False
    rec = board.get(pos)
    return is_nebula_parent(rec) if rec else False


def nebulas_enabled(game):
    """Helper to check the per-game opt-in flag."""
    return bool(game.gamestate.get("enable_nebulas"))


# Keys that mirror a regular sector record. Subsector records carry the same
# shape so consumers reading e.g. ``tile["money_pop"]`` don't KeyError.
_EMPTY_LIST_KEYS = [
    "money_pop", "money1_snap", "money2_snap",
    "moneyadv_pop", "moneyadv1_snap", "moneyadv2_snap",
    "science_pop", "science1_snap", "science2_snap",
    "scienceadv_pop", "scienceadv1_snap", "scienceadv2_snap",
    "material_pop", "material1_snap", "material2_snap",
    "materialadv_pop", "materialadv1_snap", "materialadv2_snap",
    "neutral_pop", "neutral1_snap", "neutral2_snap",
    "neutraladv_pop", "neutraladv1_snap", "neutraladv2_snap",
]


def make_subsector_record(parent_record, parent_position, subsector_letter,
                          sector_id, orientation):
    """Build a board record for a single nebula subsector.

    The record mirrors the schema of a regular sector (so any consumer that
    reads e.g. ``tile["money_pop"]`` continues to work), but with all
    population fields empty, no influence ever, only the two external edges as
    wormholes, and the subsector-specific disctile/ancient flags.
    """
    L = subsector_letter
    centre = list(SUBSECTOR_CENTERS[L])

    record = {}
    record["owner"] = 0
    record["name"] = f"{parent_record.get('name', sector_id)} ({L})"
    record["ring"] = parent_record.get("ring", 2)
    record["disctile"] = 1 if L in DISC_SUBSECTORS else 0
    record["ancient"] = 1 if L == ANCIENT_SUBSECTOR else 0
    record["guardian"] = 0
    record["gcds"] = 0
    record["warp"] = 0
    record["vp"] = 0
    record["artifact"] = 0
    record["player_ships"] = []
    for k in _EMPTY_LIST_KEYS:
        record[k] = []
    # Per-ship snap coords default to the subsector centre.
    for snap in ["int_snap", "cru_snap", "drd_snap", "sb_snap",
                 "mon_snap", "orb_snap", "ai_snap"]:
        record[snap] = list(centre)
    record["wormholes"] = list(EXTERNAL_EDGES_BY_SUBSECTOR[L])
    record["type"] = "nebula"
    record["sector"] = sector_id
    record["orientation"] = orientation
    record["parent_position"] = parent_position
    record["subsector"] = L
    record["internal_subsectors"] = [
        f"{parent_position}{other}" for other in SUBSECTOR_LETTERS if other != L
    ]
    return record


def adjacent_positions(game, pos):
    """Return a list of position keys adjacent to ``pos`` for graph traversal.

    For a nebula subsector this is the parent's external neighbour list (so
    move/explore can step out of the nebula) plus the two sibling subsectors
    (the internal wormhole connections). For everything else it is the parent
    adjacency entry from the loaded ``configs`` properties — callers should
    use :func:`adjacent_positions_from_configs` when they already have configs
    loaded; this function exists primarily for tests / lightweight callers.
    """
    parent = get_parent_position(pos) if is_nebula_subsector(pos) else pos
    # Lazy import to avoid circular deps at module load time.
    from jproperties import Properties
    configs = Properties()
    if game.gamestate.get("5playerhyperlane"):
        if game.gamestate.get("player_count") == 5:
            with open("data/tileAdjacencies_5p.properties", "rb") as f:
                configs.load(f)
        elif game.gamestate.get("player_count") == 4:
            with open("data/tileAdjacencies_4p.properties", "rb") as f:
                configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
    else:
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
    if parent not in configs:
        return []
    neighbours = list(configs.get(parent)[0].split(","))
    if is_nebula_subsector(pos):
        neighbours = neighbours + [s for s in subsectors_of(parent) if s != pos]
    return neighbours


def adjacent_positions_from_configs(game, pos, configs):
    """Like :func:`adjacent_positions` but reuses an already-loaded configs.

    For a regular hex, any neighbour that turns out to be a *nebula parent*
    is rewritten to the specific subsector that owns that external edge — so
    callers iterating neighbours never have to step through the parent
    anchor (which has no ships and no wormholes of its own).
    """
    parent = get_parent_position(pos) if is_nebula_subsector(pos) else pos
    if parent not in configs:
        return []
    raw_neighbours = list(configs.get(parent)[0].split(","))
    board = game.gamestate.get("board", {}) if game is not None else {}
    rewritten = []
    for index, n in enumerate(raw_neighbours):
        nbr_record = board.get(n)
        if nbr_record is not None and is_nebula_parent(nbr_record):
            # Translate the parent neighbour into the subsector that owns
            # the matching external edge. From `pos`'s perspective the
            # neighbour `n` sits at position `index` in the adjacency list;
            # the entry edge into `n` (board-absolute frame) is the opposite
            # direction (index + 3) % 6. Convert that into the neighbour's
            # *local* edge by adding its rotation — same convention as the
            # existing `tile_orientation_index = (index + rotation/60) % 6`
            # used everywhere else (DrawHelper, Influence.areTwoTilesAdjacent).
            entry_edge_abs = (index + 3) % 6
            nbr_rotation = int(nbr_record.get("orientation", 0)) // 60
            entry_edge_local = (entry_edge_abs + nbr_rotation) % 6
            sub_letter = None
            for L, edges in EXTERNAL_EDGES_BY_SUBSECTOR.items():
                if entry_edge_local in edges:
                    sub_letter = L
                    break
            if sub_letter is not None:
                rewritten.append(f"{n}{sub_letter}")
                continue
        rewritten.append(n)
    if is_nebula_subsector(pos):
        rewritten = rewritten + [s for s in subsectors_of(parent) if s != pos]
    return rewritten
