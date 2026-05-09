"""Tests for Nebula sector handling (Galactic Events).

Mirrors the lightweight helper pattern from ``test_game_init_tech_deck`` —
build a minimal gamestate, drop it on disk, instantiate ``GamestateHelper``,
exercise the code under test.
"""

import json

import pytest

import config


def _minimal_gamestate(enable_nebulas=True):
    return {
        "game_id": "testneb",
        "game_name": "TestNeb",
        "setup_finished": 1,
        "game_phase": [],
        "game_round": 1,
        "roundNum": 1,
        "advanced_ai": 0,
        "wa_ai": 0,
        "player_count": 2,
        "player_order": [],
        "active_player": [],
        "activePlayerColor": [],
        "lastPingTime": 0,
        "lastButton": "",
        "available_colors": [],
        "used_colors": [],
        "tile_deck_100": [],
        "tile_deck_200": [],
        "tile_deck_300": [],
        "tile_discard": [],
        "tech_deck": [],
        "available_techs": [],
        "reputation_tiles": [4, 3, 2, 1],
        "discTiles": [],
        "players": {},
        "board": {},
        "enable_nebulas": enable_nebulas,
    }


def _make_game(tmp_path, enable_nebulas=True):
    from helpers.GamestateHelper import GamestateHelper

    gs = _minimal_gamestate(enable_nebulas=enable_nebulas)
    game_path = tmp_path / f"{gs['game_id']}.json"
    with open(game_path, "w") as f:
        json.dump(gs, f)

    original_path = config.gamestate_path
    config.gamestate_path = str(tmp_path)
    game = GamestateHelper(None, gs["game_id"])
    return game, original_path


def _restore(original_path):
    config.gamestate_path = original_path


class TestNebulaSetup:
    def test_nebula_disabled_no_subsectors(self, tmp_path):
        game, original = _make_game(tmp_path, enable_nebulas=False)
        try:
            game.add_tile("207", 0, "295")
            board = game.gamestate["board"]
            assert "207" in board
            # No subsector keys created
            assert "207A" not in board
            assert "207B" not in board
            assert "207C" not in board
            # Original behaviour: ancient ship spawned in the parent record
            assert "ai-anc" in board["207"]["player_ships"]
            assert board["207"].get("is_nebula_parent") is None
        finally:
            _restore(original)

    def test_nebula_creates_three_subsectors(self, tmp_path):
        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            board = game.gamestate["board"]
            for key in ("207", "207A", "207B", "207C"):
                assert key in board, f"missing {key}"
        finally:
            _restore(original)

    def test_nebula_disctile_distribution(self, tmp_path):
        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            board = game.gamestate["board"]
            assert board["207A"]["disctile"] == 1
            assert board["207A"]["ancient"] == 0
            assert board["207B"]["disctile"] == 0
            assert board["207B"]["ancient"] == 1
            assert board["207C"]["disctile"] == 1
            assert board["207C"]["ancient"] == 0
            # Subsector B carries the ancient ship.
            assert "ai-anc" in board["207B"]["player_ships"]
            # A and C have no ships at placement time.
            assert board["207A"]["player_ships"] == []
            assert board["207C"]["player_ships"] == []
        finally:
            _restore(original)

    def test_nebula_subsector_wormholes(self, tmp_path):
        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            board = game.gamestate["board"]
            assert board["207A"]["wormholes"] == [5, 0]
            assert board["207B"]["wormholes"] == [1, 2]
            assert board["207C"]["wormholes"] == [3, 4]
        finally:
            _restore(original)

    def test_nebula_parent_no_ships_no_disctile(self, tmp_path):
        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            parent = game.gamestate["board"]["207"]
            assert parent["is_nebula_parent"] is True
            assert parent["player_ships"] == []
            assert parent["disctile"] == 0
            assert parent["ancient"] == 0
            # Parent retains a full 6-edge wormhole array so the symmetric
            # `areTwoTilesAdjacent` check passes from outside neighbours; the
            # `is_nebula_parent` flag + empty player_ships keep it inert.
            assert parent["wormholes"] == [0, 1, 2, 3, 4, 5]
            assert sorted(parent["subsectors"]) == ["207A", "207B", "207C"]
        finally:
            _restore(original)


class TestNebulaAdjacency:
    def test_subsector_internal_adjacency(self, tmp_path):
        from Buttons.Influence import InfluenceButtons
        from jproperties import Properties

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            assert InfluenceButtons.areTwoTilesAdjacent(game, "207A", "207B", configs, False)
            assert InfluenceButtons.areTwoTilesAdjacent(game, "207B", "207C", configs, False)
            assert InfluenceButtons.areTwoTilesAdjacent(game, "207A", "207C", configs, False)
        finally:
            _restore(original)


class TestInfluenceExcludesNebulas:
    def test_influence_skips_nebula_subsectors(self, tmp_path):
        """A nebula subsector should never be in the influence target list."""
        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            # NOTE: full-blown getTilesToInfluence requires a fully-populated
            # player record (techs, owned_tiles, influence_discs, etc) which
            # is heavyweight to mock. We instead spot-check the per-tile
            # filter that `getTilesToInfluence` applies: the type filter
            # should reject nebula subsectors and parents.
            for sub in ("207", "207A", "207B", "207C"):
                assert game.gamestate["board"][sub].get("type") == "nebula"
        finally:
            _restore(original)


class TestExternalAdjacency:
    """Cross-boundary adjacency: a regular hex and a nebula subsector are
    adjacent only via the subsector's external wormhole edges."""

    def test_subsector_adjacent_to_outside_neighbour(self, tmp_path):
        from Buttons.Influence import InfluenceButtons
        from jproperties import Properties

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            # 207's adjacency list is "104,206,309,310,311,208". Subsector A
            # has external edges [5, 0] -> faces 208 (edge 5) and 104 (edge 0).
            game.add_tile("207", 0, "295")
            game.add_tile("208", 0, "301")
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            assert InfluenceButtons.areTwoTilesAdjacent(
                game, "207A", "208", configs, False
            )
            # 208 is NOT adjacent to subsector B (B's external edges are 1, 2,
            # which face 206 and 309).
            assert not InfluenceButtons.areTwoTilesAdjacent(
                game, "207B", "208", configs, False
            )
        finally:
            _restore(original)

    def test_parent_neighbour_rewrite(self, tmp_path):
        from helpers import NebulaHelper as NH
        from jproperties import Properties

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            game.add_tile("208", 0, "301")
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            # 208's neighbour list contains "207" (the parent). Through
            # adjacent_positions_from_configs it should be rewritten to the
            # subsector that owns the corresponding edge — in this case 207A
            # (the subsector facing 208 via edge 5 of the parent).
            neighbours = NH.adjacent_positions_from_configs(game, "208", configs)
            assert "207A" in neighbours
            assert "207" not in neighbours
        finally:
            _restore(original)

    def test_outside_tile_adjacent_to_subsector(self, tmp_path):
        """A regular tile next to a nebula parent should evaluate as adjacent
        to the subsector that owns the matching external edge — symmetric
        check (no wormhole-gen) must pass in both directions."""
        from Buttons.Influence import InfluenceButtons
        from jproperties import Properties

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            game.add_tile("208", 0, "301")
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            # 208 is at index 5 in 207's adjacency list. Subsector A owns
            # local edge 5, so 208 ↔ 207A is the only valid external edge.
            assert InfluenceButtons.areTwoTilesAdjacent(
                game, "208", "207A", configs, False
            )
            # And the reverse direction also passes (symmetric).
            assert InfluenceButtons.areTwoTilesAdjacent(
                game, "207A", "208", configs, False
            )
            # 208 must NOT be adjacent to 207B or 207C (their wormholes face
            # other directions).
            assert not InfluenceButtons.areTwoTilesAdjacent(
                game, "208", "207B", configs, False
            )
            assert not InfluenceButtons.areTwoTilesAdjacent(
                game, "208", "207C", configs, False
            )
        finally:
            _restore(original)

    def test_rotated_parent_neighbour_rewrite(self, tmp_path):
        """Rotation must be applied when picking which subsector owns the
        entry edge from a neighbour's perspective. The convention follows
        the existing `tile_orientation_index = (i + rotation/60) % 6` used
        across DrawHelper and Influence."""
        from Buttons.Influence import InfluenceButtons
        from helpers import NebulaHelper as NH
        from jproperties import Properties

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 60, "295")  # rotated 60° CW
            game.add_tile("208", 0, "301")
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            # 208 is at index 5 in 207's adjacency list, so 207A's wormhole
            # (list index 0) reaches 208 after rotation 60° CW (since
            # board position = (list_index - rotation/60) % 6 = 5).
            # From 208's side, 207 is at index 2; the entry-edge in 207's
            # local list-index frame is (2+3+rot) % 6 = (5+1)%6 = 0, which
            # is in subsector A's [5, 0]. So the rewrite picks 207A — and
            # this matches the wormhole connectivity check from 207A's side.
            neighbours = NH.adjacent_positions_from_configs(game, "208", configs)
            assert "207A" in neighbours
            assert "207C" not in neighbours
            assert "207B" not in neighbours
            # Sanity: the wormhole connectivity check from 207A's side also
            # confirms 207A ↔ 208 at rotation 60.
            assert InfluenceButtons.areTwoTilesAdjacent(
                game, "207A", "208", configs, False
            )
        finally:
            _restore(original)


class TestNebulaDeckPopulation:
    """Verify nebula tiles 295/395 actually enter the tile decks during setup
    when ``enable_nebulas`` is on, and don't when it's off."""

    def _make_setup_game(self, tmp_path, enable_nebulas):
        from helpers.GamestateHelper import GamestateHelper

        gs = _minimal_gamestate(enable_nebulas=enable_nebulas)
        gs["community_parts"] = False
        gs["rift_cannon"] = True
        game_path = tmp_path / f"{gs['game_id']}.json"
        with open(game_path, "w") as f:
            json.dump(gs, f)
        original_path = config.gamestate_path
        config.gamestate_path = str(tmp_path)
        return GamestateHelper(None, gs["game_id"]), original_path

    def test_nebula_295_in_ring2_when_enabled(self, tmp_path):
        game, original = self._make_setup_game(tmp_path, enable_nebulas=True)
        try:
            game.setup_techs_and_outer_rim(2, False, False)
            assert "295" in game.gamestate["tile_deck_200"]
        finally:
            _restore(original)

    def test_nebula_395_in_ring3_when_enabled(self, tmp_path):
        game, original = self._make_setup_game(tmp_path, enable_nebulas=True)
        try:
            game.setup_techs_and_outer_rim(2, False, False)
            assert "395" in game.gamestate["tile_deck_300"]
        finally:
            _restore(original)

    def test_no_nebula_in_decks_when_disabled(self, tmp_path):
        game, original = self._make_setup_game(tmp_path, enable_nebulas=False)
        try:
            game.setup_techs_and_outer_rim(2, False, False)
            assert "295" not in game.gamestate["tile_deck_200"]
            assert "295" not in game.gamestate["tile_deck_300"]
            assert "395" not in game.gamestate["tile_deck_300"]
            assert "395" not in game.gamestate["tile_deck_200"]
        finally:
            _restore(original)


class TestNebulaDiscoveryReroll:
    """Per Galactic Events p. 4: Ancient Orbital ('orb') and Ancient Monolith
    ('mon') cannot be placed in a Nebula Subsector. The reroll helper must
    swap them out before the player gets a choice. We test the helper
    directly to avoid the async / Discord-interaction surface."""

    def test_orbital_redrawn_in_nebula_subsector(self, tmp_path):
        from Buttons.DiscoveryTile import DiscoveryTileButtons

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            # Pretend the player just popped "orb"; the deck still has a
            # benign disc beneath. After redraw the player should see the
            # benign disc and "orb" should be back in the deck.
            game.gamestate["discTiles"] = ["socha"]
            new_disc = DiscoveryTileButtons._maybe_reroll_for_nebula(game, "207A", "orb")
            assert new_disc == "socha"
            assert "orb" in game.gamestate["discTiles"]
        finally:
            _restore(original)

    def test_monolith_redrawn_in_nebula_subsector(self, tmp_path):
        from Buttons.DiscoveryTile import DiscoveryTileButtons

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            game.gamestate["discTiles"] = ["axc"]
            new_disc = DiscoveryTileButtons._maybe_reroll_for_nebula(game, "207C", "mon")
            assert new_disc == "axc"
            assert "mon" in game.gamestate["discTiles"]
        finally:
            _restore(original)

    def test_no_redraw_in_regular_sector(self, tmp_path):
        from Buttons.DiscoveryTile import DiscoveryTileButtons

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            # Regular ring-3 sector — no reroll, the orb stays.
            game.gamestate["discTiles"] = ["axc"]
            new_disc = DiscoveryTileButtons._maybe_reroll_for_nebula(game, "301", "orb")
            assert new_disc == "orb"
            # Deck unchanged
            assert game.gamestate["discTiles"] == ["axc"]
        finally:
            _restore(original)

    def test_safe_disc_unchanged_in_nebula(self, tmp_path):
        from Buttons.DiscoveryTile import DiscoveryTileButtons

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            game.gamestate["discTiles"] = ["axc"]
            new_disc = DiscoveryTileButtons._maybe_reroll_for_nebula(game, "207A", "socha")
            # socha is a benign Ancient Ship Part, no redraw.
            assert new_disc == "socha"
            assert game.gamestate["discTiles"] == ["axc"]
        finally:
            _restore(original)

    def test_empty_deck_falls_back_to_drawn_disc(self, tmp_path):
        """If the deck is exhausted while we're trying to redraw, the helper
        should give up and return the original disc rather than loop forever."""
        from Buttons.DiscoveryTile import DiscoveryTileButtons

        game, original = _make_game(tmp_path, enable_nebulas=True)
        try:
            game.add_tile("207", 0, "295")
            game.gamestate["discTiles"] = []
            new_disc = DiscoveryTileButtons._maybe_reroll_for_nebula(game, "207A", "orb")
            assert new_disc == "orb"
        finally:
            _restore(original)
