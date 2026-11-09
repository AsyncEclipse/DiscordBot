"""Turtugan's three faction rules.

Deep Space Explorers keeps two S3 sectors the game did not deal into its deck
as a separate reserve to draw from while exploring the outer sectors. Harvesters are
starbases that move and farm an unsettled planet. Carapace Shields is per-tile,
per-class combat state.
"""
import discord
from discord.ui import View, Button

from helpers import FactionData


class DeepSpace:
    @staticmethod
    def has_reserve(player):
        return bool(player.get("deep_space_sectors"))

    @staticmethod
    def draw_reserve(game, player):
        """Keep two undealt S3 sectors in the player's separate reserve."""
        if not FactionData.has(player, "deep_space_explorers"):
            return
        reserve = player.setdefault("deep_space_sectors", [])
        spare = game.gamestate.setdefault("sector3_spare", [])
        while len(reserve) < 2 and spare:
            reserve.append(spare.pop(0))
        game.update()

    @staticmethod
    async def post_reserve(game, player, channel):
        if not FactionData.has(player, "deep_space_explorers"):
            return
        reserve = player.get("deep_space_sectors", [])
        if not reserve:
            await channel.send(f"{player['player_name']}, there were no extra S3 sectors for Deep Space"
                               " Explorers to reserve.")
            return
        await channel.send(f"{player['player_name']}, Deep Space Explorers reserves {len(reserve)} hidden"
                           " S3 sectors in a separate stack for future Explore actions.")

    @staticmethod
    def can_offer(player, position):
        return (FactionData.has(player, "deep_space_explorers")
                and min(3, int(position) // 100) == 3
                and DeepSpace.has_reserve(player))

    @staticmethod
    def can_draw(game):
        return bool(game.gamestate.get("tile_deck_300")
                    or game.gamestate.get("tile_discard_deck_300"))

    @staticmethod
    async def offer(game, player, interaction, position):
        token = player.get("deep_space_choice_token", 0) + 1
        player["deep_space_choice_token"] = token
        player["deep_space_choice"] = position
        game.update()
        view = View()
        view.add_item(Button(label="Draw from Reserve", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{player['color']}_reservedTile_{position}_reserve_{token}"))
        if DeepSpace.can_draw(game):
            view.add_item(Button(label="Draw Random", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_reservedTile_{position}_random_{token}"))
        await interaction.channel.send(f"{player['player_name']}, Deep Space Explorers: choose a stack"
                                       " to draw an S3 sector from for this Explore action"
                                       f" ({len(player['deep_space_sectors'])} in reserve).", view=view)

    @staticmethod
    def take(game, player, position, choice, token):
        """Resolve the choice once. Returns (tileID, error)."""
        if (player.get("deep_space_choice") != position
                or str(player.get("deep_space_choice_token")) != str(token)):
            return None, "stale"
        player["deep_space_choice"] = None
        if choice == "random":
            if not DeepSpace.can_draw(game):
                game.update()
                return None, "empty"
            return game.tile_draw(position), None
        if choice != "reserve" or not DeepSpace.has_reserve(player):
            game.update()
            return None, "missing"
        tile = player["deep_space_sectors"].pop(0)
        game.update()
        return tile, None

    @staticmethod
    def keep_outer_rim(game):
        """Keep unexplored outer-sector positions available while a reserve can supply them."""
        return any(player.get("deep_space_sectors")
                   for player in game.gamestate.get("players", {}).values())


class Harvester:
    PLANET_TYPES = ("money", "science", "material", "neutral",
                    "moneyadv", "scienceadv", "materialadv", "neutraladv")
    RESOURCES = ("money", "science", "material")

    @staticmethod
    def unsettled_squares(tile):
        squares = []
        for planet in Harvester.PLANET_TYPES:
            for index, value in enumerate(tile.get(f"{planet}_pop", [])):
                if value == 0:
                    squares.append((planet, index))
        return squares

    @staticmethod
    def resource_for(square):
        for resource in Harvester.RESOURCES:
            if square.startswith(resource):
                return resource
        return None

    @staticmethod
    def occupied(game, position, square, index):
        return any(placement["position"] == position and placement["square"] == square
                   and int(placement["index"]) == int(index)
                   for player in game.gamestate.get("players", {}).values()
                   for placement in player.get("harvester_placements", []))

    @staticmethod
    def starbases(game, player, position):
        return sum(1 for ship in game.gamestate["board"].get(position, {}).get("player_ships", [])
                   if ship == f"{player['color']}-sb")

    @staticmethod
    def sectors_with_harvester(game, player):
        return [position for position in game.gamestate.get("board", {})
                if Harvester.starbases(game, player, position) > 0]

    @staticmethod
    def record(game, player, position, square, index, resource):
        if square not in Harvester.PLANET_TYPES or resource not in Harvester.RESOURCES:
            return False
        planet_resource = Harvester.resource_for(square)
        if planet_resource is not None and resource != planet_resource:
            return False
        if Harvester.starbases(game, player, position) < 1:
            return False
        index = int(index)
        pops = game.gamestate.get("board", {}).get(position, {}).get(f"{square}_pop", [])
        if index >= len(pops) or pops[index] != 0:
            return False
        if Harvester.occupied(game, position, square, index):
            return False
        placements = player.setdefault("harvester_placements", [])
        in_sector = [placement for placement in placements if placement["position"] == position]
        if len(in_sector) >= Harvester.starbases(game, player, position):
            placements.remove(in_sector[0])
        placements.append({"position": position, "square": square, "index": index, "resource": resource})
        game.update()
        return True

    @staticmethod
    def clear(game, position, color):
        player_id = game.get_player_from_color(color)
        player = game.gamestate.get("players", {}).get(player_id)
        if player is None:
            return
        placements = player.get("harvester_placements", [])
        in_sector = [placement for placement in placements if placement["position"] == position]
        # remove_units calls this before dropping the starbase, so one is about to leave.
        remaining = Harvester.starbases(game, player, position) - 1
        if len(in_sector) > remaining:
            placements.remove(in_sector[-1])
            game.update()

    @staticmethod
    def produce(game, player):
        """Upkeep: one resource per Harvester still over an unsettled planet."""
        produced = []
        round_num = game.gamestate.get("roundNum", 0)
        if player.get("harvester_produced_round") == round_num:
            return produced
        if player.get("eliminated"):
            player["harvester_placements"] = []
            player["harvester_produced_round"] = round_num
            game.update()
            return produced
        placements = player.get("harvester_placements", [])
        for placement in placements[:]:
            tile = game.gamestate.get("board", {}).get(placement["position"])
            if tile is None or f"{player['color']}-sb" not in tile.get("player_ships", []):
                placements.remove(placement)
                continue
            pops = tile.get(f"{placement['square']}_pop", [])
            if int(placement["index"]) >= len(pops) or pops[int(placement["index"])] != 0:
                placements.remove(placement)
                continue
            resource = placement["resource"]
            if resource not in Harvester.RESOURCES:
                placements.remove(placement)
                continue
            player["materials" if resource == "material" else resource] += 1
            produced.append(f"+1 {resource} in {placement['position']}")
        player["harvester_produced_round"] = round_num
        game.update()
        return produced

class Carapace:
    CLASSES = ("interceptor", "cruiser", "dread", "starbase")
    SHORT = {"interceptor": "int", "cruiser": "cru", "dread": "drd", "starbase": "sb"}

    @staticmethod
    def classes_in_battle(game, pos, color):
        ships = game.gamestate["board"][pos].get("player_ships", [])
        return [ship_class for ship_class in Carapace.CLASSES
                if f"{color}-{Carapace.SHORT[ship_class]}" in ships]

    @staticmethod
    def engaged(game, pos, color, ship_type):
        player = game.getPlayerObjectFromColor(color)
        if not FactionData.has(player, "carapace_shields"):
            return False
        state = game.gamestate["board"].get(pos, {}).get("carapaceShields", {}).get(color)
        return bool(state and state.get(ship_type))

    @staticmethod
    def weapon_damage(game, pos, color, ship_type, damage):
        if Carapace.engaged(game, pos, color, ship_type):
            return max(0, damage - 1)
        return damage

    @staticmethod
    def incoming_damage(game, pos, owner, ship_type, attacker, damage):
        if attacker == owner or damage <= 0:
            return damage
        if Carapace.engaged(game, pos, owner, ship_type):
            return max(1, damage - 1)
        return damage

    @staticmethod
    def _prompt_text(player, state, classes):
        engaged = [ship_class for ship_class in classes if state.get(ship_class)]
        if engaged:
            return (f"{player['player_name']}, Carapace Shields are engaged for: "
                    f"{', '.join(engaged)}. Press a class to engage or disengage it.")
        return (f"{player['player_name']}, Carapace Shields are disengaged. Press a class to engage it"
                " for this combat or engagement round.")

    @staticmethod
    def _view(player, pos, state, classes, token):
        view = View()
        for ship_class in classes:
            on = bool(state.get(ship_class))
            view.add_item(Button(label=f"{ship_class.capitalize()}: {'ON' if on else 'OFF'}",
                                 style=discord.ButtonStyle.green if on else discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_carapaceToggle_{pos}_{ship_class}_{token}"))
        view.add_item(Button(label="Done", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_carapaceDone_{pos}_{token}"))
        return view

    @staticmethod
    async def offer(game, channel, pos):
        tile = game.gamestate["board"].get(pos)
        if tile is None:
            return
        attacker = tile.get("attacker", [])
        defender = tile.get("defender", [])
        pairing = list(attacker) if isinstance(attacker, list) else [attacker]
        pairing += list(defender) if isinstance(defender, list) else [defender]
        for color in pairing:
            if not color or color == "ai":
                continue
            player = game.getPlayerObjectFromColor(color)
            if not FactionData.has(player, "carapace_shields"):
                continue
            classes = Carapace.classes_in_battle(game, pos, color)
            if not classes:
                continue
            state = tile.setdefault("carapaceShields", {}).setdefault(color, {})
            state["token"] = tile.get("carapaceToken", 0) + 1
            tile["carapaceToken"] = state["token"]
            state["done"] = False
            for ship_class in Carapace.CLASSES:
                state.setdefault(ship_class, False)
            game.update()
            token = state["token"]
            await channel.send(Carapace._prompt_text(player, state, classes),
                               view=Carapace._view(player, pos, state, classes, token))

    @staticmethod
    def close_controls(game, pos):
        for state in game.gamestate["board"][pos].get("carapaceShields", {}).values():
            state["done"] = True
        game.update()

    @staticmethod
    async def toggle(game, player, interaction, customID):
        pos, ship_class, token = customID.split("_")[1:4]
        state = game.gamestate["board"].get(pos, {}).get("carapaceShields", {}).get(player["color"])
        if (state is None or state.get("done") or str(state.get("token")) != token
                or ship_class not in Carapace.classes_in_battle(game, pos, player["color"])):
            await interaction.followup.send("These Carapace Shields controls are no longer current.",
                                            ephemeral=True)
            return
        state[ship_class] = not state.get(ship_class, False)
        game.update()
        classes = Carapace.classes_in_battle(game, pos, player["color"])
        await interaction.message.edit(content=Carapace._prompt_text(player, state, classes),
                                       view=Carapace._view(player, pos, state, classes, token))

    @staticmethod
    async def done(game, player, interaction, customID):
        pos, token = customID.split("_")[1:3]
        state = game.gamestate["board"].get(pos, {}).get("carapaceShields", {}).get(player["color"])
        if state is None or state.get("done") or str(state.get("token")) != token:
            await interaction.followup.send("This Carapace Shields prompt was already resolved.", ephemeral=True)
            return
        state["done"] = True
        game.update()
        engaged = [ship_class for ship_class in Carapace.CLASSES if state.get(ship_class)]
        await interaction.message.edit(view=None)
        await interaction.channel.send(f"{player['player_name']} finished setting Carapace Shields: "
                                       f"{', '.join(engaged) if engaged else 'none engaged'}.")

    @staticmethod
    def has_pending_missiles(game, pos):
        return bool(game.gamestate["board"].get(pos, {}).get("carapacePendingMissiles"))

    @staticmethod
    async def prompt_missile(game, interaction, pos, color, ship_type, computer, speed,
                             dieNum, dieDam, counter, ignore_shields=False):
        from helpers.CombatHelper import Combat
        tile = game.gamestate["board"][pos]
        token = tile.get("carapaceMissileToken", 0) + 1
        tile["carapaceMissileToken"] = token
        tile.setdefault("carapaceRollOldLength", len(Combat.findPlayersInTile(game, pos)))
        tile.setdefault("carapacePendingMissiles", []).append({
            "token": token, "color": color, "shipType": ship_type, "computer": computer,
            "speed": speed, "dieNum": dieNum, "dieDam": dieDam, "counter": counter,
            "ignoreShields": ignore_shields})
        game.update()
        view = View()
        targets = Combat.getOpponentUnitsThatCanBeHit(
            game, color, tile["player_ships"], dieNum, computer, pos, speed, ignore_shields)
        for target in targets:
            owner, short_type = target.split("-")
            label, emoji = Combat.getTargetButton(game, pos, target)
            modes = (("damage", "-1 Damage"), ("hit", "-1 to Hit")) if Carapace.engaged(
                game, pos, owner, Combat.translateShipAbrToName(short_type)) else (("normal", "Hit"),)
            for mode, penalty in modes:
                view.add_item(Button(label=f"{label}: {penalty}", emoji=emoji,
                                     style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{color}_carapaceMissile_{pos}_{mode}_{token}_{target}"))
        await interaction.channel.send(f"{game.getPlayerObjectFromColor(color)['player_name']}, choose the"
                                       f" target for your missile die ({dieNum}). Against engaged Carapace"
                                       " Shields, choose -1 damage or -1 to hit.", view=view)

    @staticmethod
    async def resolve_missile(game, player, interaction, customID):
        pos, mode, token, target = customID.split("_")[1:5]
        if mode not in ("damage", "hit", "normal"):
            return
        tile = game.gamestate["board"].get(pos, {})
        pending = tile.get("carapacePendingMissiles", [])
        entry = next((item for item in pending if str(item["token"]) == token
                      and item["color"] == player["color"]), None)
        if entry is None:
            await interaction.followup.send("This missile choice was already resolved.", ephemeral=True)
            return
        from helpers.CombatHelper import Combat
        owner, short_type = target.split("-")
        shielded = Carapace.engaged(game, pos, owner, Combat.translateShipAbrToName(short_type))
        targets = Combat.getOpponentUnitsThatCanBeHit(
            game, entry["color"], tile["player_ships"], entry["dieNum"], entry["computer"],
            pos, entry["speed"], entry["ignoreShields"])
        if targets and target not in targets:
            pending.remove(entry)
            await Carapace.prompt_missile(
                game, interaction, pos, entry["color"], entry["shipType"], entry["computer"],
                entry["speed"], entry["dieNum"], entry["dieDam"], entry["counter"], entry["ignoreShields"])
            await interaction.message.edit(view=None)
            return
        if targets and shielded != (mode != "normal"):
            await interaction.followup.send("That missile target or shield choice is no longer available.",
                                            ephemeral=True)
            return
        pending.remove(entry)
        game.update()
        if shielded:
            await interaction.channel.send(
                f"{player['player_name']} chose Carapace Shields'"
                f" {'-1 to Hit' if mode == 'hit' else '-1 Damage'} for the missile die ({entry['dieNum']}).")
        computer = entry["computer"] - (1 if mode == "hit" else 0)
        # "-1 Damage" is the shield's own reduction (incoming_damage); "!" marks -1 to Hit, which replaces it
        damage = entry["dieDam"] if mode == "damage" else f"{entry['dieDam']}!"
        ships = tile["player_ships"][:]
        hittable = Combat.getOpponentUnitsThatCanBeHit(game, entry["color"], ships, entry["dieNum"],
                                                       computer, pos, entry["speed"], entry["ignoreShields"])
        if target in hittable:
            await Combat.offerHitPrompt(game, interaction, pos, entry["color"], [target],
                                        entry["dieNum"], damage, entry["counter"], deferEnd=True)
        if not pending:
            old_length = tile.pop("carapaceRollOldLength", len(Combat.findPlayersInTile(game, pos)))
            if len(Combat.findPlayersInTile(game, pos)) != old_length:
                await Combat.checkCombatEnd(game, interaction, pos, old_length)
            elif not tile.get("unresolvedHits", 0):
                await Combat.promptNextSpeed(game, pos, interaction.channel, True)
            game.update()
        await interaction.message.edit(view=None)

    @staticmethod
    def clear(game, pos):
        tile = game.gamestate["board"].get(pos)
        if tile is None:
            return
        tile.pop("carapaceShields", None)
        tile.pop("carapacePendingMissiles", None)
        tile.pop("carapaceRollOldLength", None)
        game.update()
