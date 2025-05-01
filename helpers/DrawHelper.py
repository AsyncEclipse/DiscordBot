import math
import discord
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties
import json
import os
from discord.ui import View, Button

from helpers.ImageCache import ImageCacheHelper
from helpers.ShipHelper import PlayerShip


class DrawHelper:
    def __init__(self, gamestate):
        self.gamestate = gamestate

    def use_image(self, filename):
        image_cache = ImageCacheHelper("images/resources")  # Get the singleton instance
        image = image_cache.get_image(filename)
        fineToGetOrig = any(["Alone" in filename,
                             "masks" in filename,
                             "basic_ships" in filename,
                             "factions" in filename,
                             "reference" in filename,
                             "technology" in filename,
                             "upgrades" in filename])
        if image:
            if fineToGetOrig:
                return image
            else:
                return image.copy()
        else:
            filename = filename.split("/")[len(filename.split("/")) - 1]
            image = image_cache.get_image(filename)
            if image:
                if fineToGetOrig:
                    return image
                else:
                    return image.copy()
            else:
                print(filename)

    def get_short_faction_name(self, full_name):
        if full_name == "Descendants of Draco":
            return "draco"
        elif full_name == "Mechanema":
            return "mechanema"
        elif full_name == "Planta":
            return "planta"
        elif full_name == "Orian Hegemony" or full_name == "Orion Hegemony":
            return "orion"
        elif full_name == "Hydran Progress":
            return "hydran"
        elif full_name == "Eridani Empire":
            return "eridani"
        elif full_name == "Wardens of Magellan":
            return "magellan"
        elif full_name == "Enlightened of Lyra":
            return "lyra"
        elif full_name == "Rho Indi Syndicate":
            return "rho"
        elif full_name == "The Exiles":
            return "exile"
        elif "Terran" in full_name:
            return full_name.lower().replace(" ", "_")

    def base_tile_image(self, sector):
        filepath = f"images/resources/hexes/{str(sector)}.png"
        if os.path.exists(filepath):
            tile_image = self.use_image(filepath)
            return tile_image

    def base_tile_image_with_rotation(self, sector, rotation, wormholes):
        wormholeCode = ""
        filepath = f"images/resources/hexes/{str(sector)}.png"
        if os.path.exists(filepath):
            tile_image = self.use_image(filepath)
        mult = 1024/345
        closedpath = "images/resources/masks/closed_wh_mask.png"
        openpath = "images/resources/masks/open_wh_mask.png"
        closed_mask = self.use_image(closedpath)
        open_mask = self.use_image(openpath)
        for wormhole in wormholes:
            wormholeCode += str(wormhole)
        for i in range(6):
            tile_orientation_index = (i + 6 + int(rotation / 60)) % 6
            if tile_orientation_index in wormholes:
                tile_image.paste(open_mask, (int(154 * mult), 0), mask=open_mask)
            else:
                tile_image.paste(closed_mask, (int(154 * mult), 0), mask=closed_mask)
            tile_image = tile_image.rotate(60)
        return tile_image

    def draw_possible_oritentations(self, tileID, position, playerTiles, view: View, player):
        count = 1
        mult = 1
        context = Image.new("RGBA", (int(345 * 3 * 3 * mult),
                                     int(300 * 3 * 2 * mult) + int(10 * mult)),
                            (255, 255, 255, 0))
        configs = Properties()
        configs2 = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
                configs2.load(f)
        if self.gamestate.get("5playerhyperlane"):
            if self.gamestate.get("player_count") == 5:
                with open("data/tileAdjacencies_5p.properties", "rb") as f:
                    configs.load(f)
            elif self.gamestate.get("player_count") == 4:
                with open("data/tileAdjacencies_4p.properties", "rb") as f:
                    configs.load(f)
            else:
                with open("data/tileAdjacencies.properties", "rb") as f:
                    configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
        with open("data/sectors.json") as f:
            tile_data = json.load(f)
        tile = tile_data[tileID]
        wormholeStringsViewed = []

        def contains_all_chars(wormhole_string1, wormhole_string2):
            set1 = set(wormhole_string1)
            set2 = set(wormhole_string2)

            return set1.issubset(set2)
        for x in range(6):
            rotation = 60 * x
            wormholeString = ''.join(str((wormhole + x) % 6) for wormhole in tile["wormholes"])
            alreadyFound = False
            for string in wormholeStringsViewed:
                if contains_all_chars(string, wormholeString):
                    alreadyFound = True
            if alreadyFound:
                continue
            wormholeStringsViewed.append(wormholeString)
            rotationWorks = False
            for index, adjTile in enumerate(configs.get(position)[0].split(",")):
                adjTileWormholeNum = (index + x) % 6
                if rotationWorks:
                    continue
                if adjTile in playerTiles and adjTileWormholeNum in tile["wormholes"]:
                    for index2, adjTile2 in enumerate(configs.get(adjTile)[0].split(",")):
                        tile_orientation_index2 = (index2 +
                                                   int(self.gamestate["board"][adjTile]["orientation"]) // 60) % 6
                        if all([adjTile2 == position,
                                tile_orientation_index2 in self.gamestate["board"][adjTile]["wormholes"]]):
                            rotationWorks = True
                            break
            if rotationWorks:
                context2 = self.base_tile_image_with_rotation_in_context(rotation, tileID, tile, count,
                                                                         configs, position, configs2)
                context.paste(context2, (int(345 * 3 * ((count - 1) % 3) * mult),
                                         int(910 * (int((count - 1) / 3)) * mult)),
                              mask=context2)
                view.add_item(Button(label="Option #" + str(count),
                                     style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_placeTile_{position}_{tileID}_{rotation}"))
                count += 1
        byteData = BytesIO()
        if count < 5:
            context = context.crop((0, 0, int(345 * 3 * (count - 1) * mult), int(300 * 3 * mult)))
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="tile_image.webp")
        return view, file

    def base_tile_image_with_rotation_in_context(self, rotation, tileID, tile, count, configs, position, configs2):
        mult = 1
        context = Image.new("RGBA", (int(345 * 3 * mult), int(300 * 3 * mult)), (255, 255, 255, 0))
        image = self.base_tile_image_with_rotation(tileID, rotation, tile["wormholes"]).resize((345, 300))
        context.paste(image, (int(345 * mult), int(300 * mult)), mask=image)
        coords = [(int(345 * mult), 0),
                  (int(605 * mult), int(150 * mult)),
                  (int(605 * mult), int(450 * mult)),
                  (int(345 * mult), int(600 * mult)),
                  (int(85 * mult), int(450 * mult)),
                  (int(85 * mult), int(150 * mult))]
        
        for index, adjTile in enumerate(configs.get(position)[0].split(",")):
            additionalRot = 0
            adjTile2 = configs2.get(position)[0].split(",")[index]
            if adjTile != adjTile2:
                additionalRot = 60
                if position in ["105", "208", "312","415", "303","202","102","403"]:
                    additionalRot = -60
            if adjTile in self.gamestate["board"]:
                adjTileImage = self.board_tile_image(adjTile, additionalRot).resize((345, 300))
                context.paste(adjTileImage, coords[index], mask=adjTileImage)
        font = ImageFont.truetype("images/resources/arial.ttf", size=80)
        ImageDraw.Draw(context).text((10, 10), f"Option #{count}", (255, 255, 255), font=font,
                                     stroke_width=2, stroke_fill=(0, 0, 0))
        return context

    def board_tile_image_file(self, position):
        final_context = self.board_tile_image(position)
        bytes_io = BytesIO()
        final_context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tile_image.webp")

    def availablePartsFile(self, available_parts):
        available_parts.discard("empty")
        amount = len(available_parts)
        result = math.ceil(math.sqrt(amount))
        height = math.ceil(amount / result)
        context = Image.new("RGBA", (262 * result, 262 * height), (255, 255, 255, 0))

        with open("data/parts.json", "r") as f:
            part_data = json.load(f)
        for count, part in enumerate(available_parts):
            part_details = part_data.get(part)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else part
            part_path = f"images/resources/components/upgrades/{partName}.png"
            part_image = Image.open(part_path).resize((256, 256))
            x = count % result
            y = int(count / result)
            context.paste(part_image, (262 * x, 262 * y))
        # context = Image.new("RGBA", (260 * (len(available_parts)), 256), (255, 255, 255, 0))

        # for x,part in enumerate(available_parts):
        #     part_details = part_data.get(part)
        #     partName = part_details["name"].lower().replace(" ", "_") if part_details else part
        #     part_path = f"images/resources/components/upgrades/{partName}.png"
        #     part_image = Image.open(part_path).resize((256,256))
        #     context.paste(part_image,(x * 259, 0))

        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="parts.webp")

    def mergeLocationsFile(self, locations):
        amount = len(locations)
        mult = 1024 / 345
        result = math.ceil(math.sqrt(amount))
        height = math.ceil(amount / result)
        context = Image.new("RGBA", (int(360 * mult * result), int(315 * mult * height)), (255, 255, 255, 0))

        for count, tile in enumerate(locations):
            image = self.board_tile_image(tile)
            x = count % result
            y = int(count / result)
            context.paste(image, (int(360 * mult * x), int(315 * mult * y)))
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tiles.webp")

    def board_tile_image(self, position, additionalRot:int=0):
        sector = self.gamestate["board"][position]["sector"]
        filepath2 = f"images/resources/hexes/{sector}.png"
        filepath = f"images/resources/hexes/numberless/{sector}.png"
        numberless = True
        mult = 1024 / 345
        if not os.path.exists(filepath):
            filepath = filepath2
            numberless = False
        if os.path.exists(filepath):
            tile_image = self.use_image(filepath)
            tile = self.gamestate["board"][position]
            rotation = (int(tile["orientation"])+additionalRot+360)%360

            if int(position) // 100 == 2 and int(position) % 2 == 1 and self.gamestate["player_count"] < 7:
                hsMask2 = Image.open("images/resources/masks/hsmaskTrip.png").convert("RGBA").resize((210, 210))
                tile_image.paste(hsMask2, (int(138 * mult), int(115 * mult)), mask=hsMask2)
            if tile.get("disctile", 0) > 0:
                discPath = "images/resources/components/discovery_tiles/discovery_2ptback.png"
                discTile = self.use_image(discPath)
                discTile = discTile.rotate(315, expand=True)
                if "bh" in tile.get("type", []):
                    tile_image.paste(discTile, (int(12 * mult), int(89 * mult)), mask=discTile)
                else:
                    tile_image.paste(discTile, (int(108 * mult), int(89 * mult)), mask=discTile)

            text_position = (int(280 * mult), int(132 * mult))
            bannerPath = "images/resources/masks/banner.png"
            banner = self.use_image(bannerPath)
            if not numberless and "back" not in sector:
                tile_image.paste(banner, (int(247 * mult), int(126 * mult)), mask=banner)

            font = ImageFont.truetype("images/resources/arial.ttf", size=int(30 * mult))
            text = str(position)
            stroke_color = (0, 0, 0)
            stroke_width = 6
            text_color = (255, 255, 255)
            textDrawableImage = ImageDraw.Draw(tile_image)
            textDrawableImage.text(text_position, text, text_color, font=font,
                                   stroke_width=stroke_width, stroke_fill=stroke_color)

            wormholeCode = ""
            closedpath = "images/resources/masks/closed_wh_mask.png"
            openpath = "images/resources/masks/open_wh_mask.png"
            greenpath = "images/resources/masks/orange_open_wh_mask.png"
            closed_mask = self.use_image(closedpath)
            open_mask = self.use_image(openpath)
            green = self.use_image(greenpath)
            configs = Properties()
            if self.gamestate.get("5playerhyperlane"):
                if self.gamestate.get("player_count") == 5:
                    with open("data/tileAdjacencies_5p.properties", "rb") as f:
                        configs.load(f)
                elif self.gamestate.get("player_count") == 4:
                    with open("data/tileAdjacencies_4p.properties", "rb") as f:
                        configs.load(f)
                else:
                    with open("data/tileAdjacencies.properties", "rb") as f:
                        configs.load(f)
            else:
                with open("data/tileAdjacencies.properties", "rb") as f:
                    configs.load(f)
            if "wormholes" in tile and tile.get("type","")!="exploded":
                for wormhole in tile["wormholes"]:
                    wormholeCode += str(wormhole)
                for i in range(6):
                    tile_orientation_index = (i + int(rotation / 60)) % 6
                    if tile_orientation_index in tile["wormholes"]:
                        found = False
                        for x, adjTile in enumerate(configs.get(position)[0].split(",")):
                            if x == i and self.areTwoTilesAdjacent(position, adjTile, configs) and additionalRot==0:
                                tile_image.paste(green, (int(152 * mult), 0), mask=green)
                                found = True
                                break
                        if not found:
                            tile_image.paste(open_mask, (int(152 * mult), 0), mask=open_mask)
                    else:
                        tile_image.paste(closed_mask, (int(152 * mult), 0), mask=closed_mask)
                    if isinstance(tile.get("owner"), str):
                        if not self.gamestate.get("turnOffLines"):
                            colorOwner = tile["owner"]
                            playerObj = self.getPlayerObjectFromColor(colorOwner)
                            for x, adjTile in enumerate(configs.get(position)[0].split(",")):
                                if x == i:
                                    if adjTile not in playerObj["owned_tiles"]:
                                        linepath = f"images/resources/masks/{colorOwner}_line.png"
                                        line = self.use_image(linepath)
                                        tile_image.paste(line, (int(78 * mult), 0), mask=line)
                                    break
                    tile_image = tile_image.rotate(60)
            if "warpDisc" in tile or "warpPoint" in tile:
                warppath = "images/resources/all_boards/Warp_picture.png"
                warp_mask = self.use_image(warppath)
                tile_image.paste(warp_mask, (int(20 * mult), int(140 * mult)), mask=warp_mask)
            if len(tile.get("player_ships", [])) > 0:
                counts = {}  # To track counts for each ship type
                countsShips = {}
                for ship in tile["player_ships"]:
                    if "-" not in ship:
                        continue
                    ship_type = ship.split("-")[1]  # Extract ship type
                    size = int(70 * mult)
                    if ship not in countsShips:
                        countsShips[ship] = 0
                    countsShips[ship] += int(10 * mult)
                    if ship_type in ["gcds", "gcdsadv", "anc", "ancadv", "grd", "grdadv"]:
                        ship = ship_type.replace("adv", "")
                        ship_type = "ai"
                        size = int(110 * mult)
                    if ship_type == "orb" or ship_type == "mon":
                        ship = ship_type
                        if ship_type == "orb":
                            size = int(110 * mult)
                            if tile["owner"] != 0:
                                if all([self.getPlayerObjectFromColor(tile["owner"])['name'] == "The Exiles",
                                            tile.get("orbital_pop", [0])[0] == 1]):
                                    ship = "exile_orb"
                                
                    filepathShip = f"images/resources/components/fancy_ships/fancy_{ship}.png"
                    if self.gamestate.get("fancy_ships") and os.path.exists(filepathShip):
                        filepathShip = f"images/resources/components/fancy_ships/fancy_{ship}.png"
                    else:
                        filepathShip = f"images/resources/components/basic_ships/{ship}.png"
                    if ship_type == "None":
                        continue
                    ship_image = self.use_image(filepathShip)

                    coords = tile[f"{ship_type}_snap"]

                    if ship_type not in counts:
                        counts[ship_type] = 0
                    xCordToUse = coords[0]
                    yCordToUse = coords[1]
                    if "drd" in ship_type or "cru" in ship_type:
                        xCordToUse -= 30
                        yCordToUse -= 30
                    if "sb" in ship_type:
                        yCordToUse -= 30

                    tile_image.paste(ship_image,
                                     (int(345 / 1024 * mult * xCordToUse + (counts[ship_type] - size / 2)),
                                      int(345 / 1024 * mult * yCordToUse + (counts[ship_type] - size / 2))),
                                     mask=ship_image)
                    counts[ship_type] += int(10 * mult)
                    if ship_type == "ai":
                        counts[ship_type] += int(20 * mult)
                for key, value in countsShips.items():
                    damage = 0
                    ship_type = "ai"
                    if "ai-" not in key:
                        ship_type = key.split("-")[1]

                    coords = tile[ship_type.replace("adv", "") + "_snap"]
                    if "damage_tracker" in self.gamestate["board"][position]:
                        if key in self.gamestate["board"][position]["damage_tracker"]:
                            damage = self.gamestate["board"][position]["damage_tracker"][key]
                    if damage > 0:
                        for count in range(damage):
                            damage_image = self.use_image("images/resources/components/basic_ships/marker_damage.png")
                            tile_image.paste(damage_image,
                                             (int(345 / 1024 * mult * coords[0] + value - size / 2 +
                                                  10 * count * mult + 15 * mult),
                                              int(345 / 1024 * mult * coords[1] + value - size / 2 + 35 * mult)),
                                             mask=damage_image)

            def paste_resourcecube(tile, tile_image, resource_type, color):
                if tile.get(f"{resource_type}_pop", 0):
                    if f"{resource_type}_shrine" in tile:
                        shrine_path = "images/resources/components/factions/shrine.png"
                        shrine_image = self.use_image(shrine_path).resize((60, 60))
                        coords = tile[f"{resource_type}1_snap"]
                        if coords is None or coords == []:
                            coords = tile[f"{resource_type}adv1_snap"]
                        tile_image.paste(shrine_image, (int(345 / 1024 * mult * coords[0] - int(38 * mult)),
                                                        int(345 / 1024 * mult * coords[1] - int(38 * mult))),
                                         mask=shrine_image)
                    popSize = tile[f"{resource_type}_pop"][0]
                    if len(tile[f"{resource_type}_pop"]) > 1:
                        popSize += tile[f"{resource_type}_pop"][1]
                    for x in range(popSize):
                        if x + 1 <= len(tile[f"{resource_type}_pop"]):
                            pop_path = f"images/resources/components/all_boards/popcube_{color}.png"
                            pop_image = self.use_image(pop_path)
                            if resource_type == "orbital":
                                coords = tile["orb_snap"]
                            else:
                                coords = tile[f"{resource_type}{x + 1}_snap"]
                            tile_image.paste(pop_image, (int(345 / 1024 * mult * coords[0] - int(18 * mult)),
                                                         int(345 / 1024 * mult * coords[1] - int(18 * mult))),
                                             mask=pop_image)
                            if "money" in resource_type or "science" in resource_type or "material" in resource_type:
                                resource_type2 = resource_type.replace("adv", "") + "_Alone"
                                pop_path = f"images/resources/components/resourcesymbols/{resource_type2}.png"
                                pop_image = self.use_image(pop_path)
                                tile_image.paste(pop_image, (int(345 / 1024 * mult * coords[0] - int(13 * mult)),
                                                             int(345 / 1024 * mult * coords[1] - int(13 * mult))),
                                                 mask=pop_image)

            if tile.get("owner", 0) != 0:
                color = tile["owner"]
                inf_path = f"images/resources/components/all_boards/influence_disc_{color}.png"
                inf_image = self.use_image(inf_path)
                if "currentAction" in tile:
                    if tile["currentAction"] == "move":
                        tile_image.paste(inf_image, (int(202 * mult), int(30 * mult)), mask=inf_image)
                    elif tile["currentAction"] == "build":
                        tile_image.paste(inf_image, (int(202 * mult), int(180 * mult)), mask=inf_image)
                    else:
                        tile_image.paste(inf_image, (int(82 * mult), int(148 * mult)), mask=inf_image)

                else:
                    tile_image.paste(inf_image, (int(153 * mult), int(130 * mult)), mask=inf_image)
                for resource in ["neutral", "neutraladv", "money", "moneyadv",
                                 "science", "scienceadv", "material", "materialadv", "orbital"]:
                    paste_resourcecube(tile, tile_image, resource, color)
            return tile_image

    def areTwoTilesAdjacent(self, tile1, tile2, configs):
        def is_adjacent(tile_a, tile_b):
            if tile_a in configs and tile_a in self.gamestate["board"]:
                for index, adjTile in enumerate(configs.get(tile_a)[0].split(",")):
                    tile_orientation_index = (index + int(self.gamestate["board"][tile_a]["orientation"] // 60)) % 6
                    if all([adjTile == tile_b,
                            tile_orientation_index in self.gamestate["board"][tile_a].get("wormholes", [])]):
                        return True
            return False

        return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)

    def display_techs(self, message:str, techs):
        context = Image.new("RGBA", (2500 * 3, 450 * 3), (0, 0, 0, 255))
        techsAvailable = techs
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        with open("data/parts.json", "r") as f:
            part_data = json.load(f)

        tech_groups = {
            "nano": [],
            "grid": [],
            "military": [],
            "any": []
        }
        # Group techs by type and calculate their costs
        for tech in techsAvailable:
            tech_details = tech_data.get(tech)
            if tech_details:
                tech_type = tech_details["track"]
                cost = tech_details["base_cost"]
                tech_groups[tech_type].append((tech, tech_details["name"], cost))
        x1 = -0.7
        x2 = -0.7
        x3 = -0.7
        x4 = -0.7
        largestX = 760
        ultimateX = 0
        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=100)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        text_drawable_image.text((60, 0), message, (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        for tech_type in tech_groups:
            sorted_techs = sorted(tech_groups[tech_type], key=lambda x: x[2])  # Sort by cost
            size = 290
            last_tech = "bleh"
            for tech, tech_name, cost in sorted_techs:
                tech_details = tech_data.get(tech)
                techName = tech_details["name"].lower().replace(" ", "_") if tech_details else tech
                if tech_type == "military":
                    y = int(size * 0.25)
                    x1 += 1
                    if techName == last_tech:
                        x1 -= 0.7
                    ultimateX = int(x1 * size)
                if tech_type == "grid":
                    y = int(size * 1.25)
                    x2 += 1
                    if techName == last_tech:
                        x2 -= 0.7
                    ultimateX = int(x2 * size)
                elif tech_type == "nano":
                    y = int(size * 2.25)
                    x3 += 1
                    if techName == last_tech:
                        x3 -= 0.7
                    ultimateX = int(x3 * size)
                elif tech_type == "any":
                    y = int(size * 3.25)
                    x4 += 1
                    if techName == last_tech:
                        x4 -= 0.7
                    ultimateX = int(x4 * size)

                tech_path = f"images/resources/components/technology/{tech_type}/tech_{techName}.png"
                ultimateX += 50
                y += 50
                if not os.path.exists(tech_path):
                    tech_path = f"images/resources/components/technology/rare/tech_{techName}.png"
                tech_image = Image.open(tech_path)
                # tech_image = self.use_image(tech_path)
                # tech_image = tech_image.resize((73,73))
                context.paste(tech_image, (ultimateX, y), mask=tech_image)
                # if part_data.get(tech, {}).get("nrg_use", 0) > 0:
                #     energy_image = self.use_image("images/resources/components/energy/" +
                #                                   f"{str(part_data[tech]['nrg_use'])}energy.png")
                #     context.paste(energy_image, (ultimateX + 207, y + 50), mask=energy_image)
                largestX = max(largestX, ultimateX + 270)
                last_tech = techName
        context = context.crop((0, 0, largestX, 450 * 3))
        return context

    def display_remaining_discoveries(self):
        tiles = self.gamestate["discTiles"][:]
        sorted_tiles = sorted(tiles)
        context = Image.new("RGBA", (85 * len(tiles), 90), (0, 0, 0, 255))
        count = 0
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        for tile in sorted_tiles:
            discName = discTile_data[tile]["name"]
            part_path = ("images/resources/components/discovery_tiles/discovery"
                         f"_{discName.replace(' ', '_').lower()}.png")
            part_image = self.use_image(part_path).resize((80, 80))
            context.paste(part_image, (85 * count, 0), mask=part_image)
            count += 1
        return context

    def display_turn_order(self):
        context = Image.new("RGBA", (900, 290), (0, 0, 0, 255))
        if len(self.gamestate.get("activePlayerColor", [])) == 1:
            activeColor = self.gamestate["activePlayerColor"][0]
        else:
            return context
        for activePlayer in self.gamestate["players"].values():
            if activePlayer["color"] == activeColor:
                break
        else:
            return context

        if len(self.gamestate.get("turn_order", [])) < self.gamestate["player_count"]:
            listHS = [201, 203, 205, 207, 209, 211]
            if self.gamestate["player_count"] > 6:
                listHS = [302,304,306,308,310,312,314,316,318]
            playerHSID = activePlayer["home_planet"]
            tileLoc = next((tile for tile in self.gamestate["board"]
                                     if self.gamestate["board"][tile]["sector"] == str(playerHSID)), None)
            if tileLoc == None:
                return context
            tileLocation = int(tileLoc)
            index = listHS.index(tileLocation)
            if index is None:
                return context
            listHS = listHS[index:] + listHS[:index]
            playerOrder = []
            for number in listHS:
                if str(number) not in self.gamestate["board"]:
                    continue
                tileID = self.gamestate["board"][str(number)]["sector"]
                nextPlayer = next((player for player in self.gamestate["players"].values()
                                   if player["home_planet"] == str(tileID)), None)
                if nextPlayer is not None:
                    playerOrder.append(nextPlayer)
        else:
            listPlayers = self.gamestate["turn_order"]
            if activePlayer["player_name"] not in listPlayers:
                return context
            index = listPlayers.index(activePlayer["player_name"])
            listPlayers = listPlayers[index:] + listPlayers[:index]
            playerOrder = []
            for player_name in listPlayers:
                nextPlayer = next((player for player in self.gamestate["players"].values()
                                   if player["player_name"] == player_name), None)
                if nextPlayer is not None:
                    playerOrder.append(nextPlayer)

        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=70)
        font_smaller = ImageFont.truetype("images/resources/arial.ttf", size=35)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        text_drawable_image.text((0, 0), "Turn Order:", (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)

        for n, player in enumerate(playerOrder):
            border = 6
            faction = self.get_short_faction_name(player["name"])
            pop_path = f"images/resources/components/all_boards/popcube_{player['color']}.png"
            pop_image = self.use_image(pop_path)
            pop_image = pop_image.crop((32, 32, pop_image.width - 32, pop_image.height - 32))
            pop_image = pop_image.resize((90, 90))
            context.paste(pop_image, (95*n, 85), mask=pop_image)
            face_tile_path = f"images/resources/components/factions/{faction}_board.png"
            face_tile_image = self.use_image(face_tile_path)
            face_tile_image = face_tile_image.crop((49, 252, 154, 357))
            face_tile_image = face_tile_image.resize((90 - 2 * border, 90 - 2 * border))
            context.paste(face_tile_image, (95 * n + border, 85 + border), mask=face_tile_image)
            if player["passed"]:
                draw = ImageDraw.Draw(context)
                draw.line((95 * n, 85, 95 * n + 90, 85 + 90), (0, 0, 0), 8)
                draw.line((95 * n, 85 + 90, 95 * n + 90, 85), (0, 0, 0), 8)
                draw.line((95 * n, 85, 95 * n + 90, 85 + 90), (255, 255, 255), 4)
                draw.line((95 * n, 85 + 90, 95 * n + 90, 85), (255, 255, 255), 4)

        if len(self.gamestate.get("pass_order", [])) == 0:
            return context

        text_drawable_image.text((0, 195), "Next", (0, 255, 0), font=font_smaller,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        text_drawable_image.text((0, 225), "Round:", (0, 255, 0), font=font_smaller,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)

        for n, player_name in enumerate(self.gamestate["pass_order"]):
            player = next((player for player in self.gamestate["players"].values()
                           if player["player_name"] == player_name), None)
            if player is None:
                continue
            border = 4
            faction = self.get_short_faction_name(player["name"])
            pop_path = f"images/resources/components/all_boards/popcube_{player['color']}.png"
            pop_image = self.use_image(pop_path)
            pop_image = pop_image.crop((32, 32, pop_image.width - 32, pop_image.height - 32))
            pop_image = pop_image.resize((60, 60))
            context.paste(pop_image, (130 + 65 * n, 200), mask=pop_image)
            face_tile_path = f"images/resources/components/factions/{faction}_board.png"
            face_tile_image = self.use_image(face_tile_path)
            face_tile_image = face_tile_image.crop((49, 252, 154, 357))
            face_tile_image = face_tile_image.convert("L").convert("RGBA")
            face_tile_image = face_tile_image.resize((60 - 2 * border, 60 - 2 * border))
            context.paste(face_tile_image, (130 + 65 * n + border, 200 + border), mask=face_tile_image)

        return context

    def display_remaining_tiles(self):
        context = Image.new("RGBA", (1900, 500), (0, 0, 0, 255))

        filepath = "images/resources/hexes/sector3backblank.png"
        tile_image = self.use_image(filepath).resize((172, 150))
        context.paste(tile_image, (370, 115), mask=tile_image)
        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=70)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        amount = len(self.gamestate["tile_deck_300"])

        if "tile_discard_deck_300" in self.gamestate:
            amount += len(self.gamestate["tile_discard_deck_300"])

        text_drawable_image.text((565, 140), str(amount), (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        text_drawable_image.text((0, 140), "Remaining           :", (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        if "roundNum" in self.gamestate:
            rnd = self.gamestate["roundNum"]
        else:
            rnd = 1
        text_drawable_image.text((0, 0), "Round #" + str(rnd), (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)

        text_drawable_image.text((0, 270), "AI Stats:", (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        x = 0
        for ship_type in ["anc", "grd", "gcds"]:
            adv = ""
            if self.gamestate["advanced_ai"]:
                adv = "adv"
            if self.gamestate.get("wa_ai"):
                adv = "wa"
            if ship_type+"_type" in self.gamestate:
                advanced = "adv" in self.gamestate[ship_type+"_type"]
                worldsafar ="wa" in self.gamestate[ship_type+"_type"]
                if advanced:
                    adv = "adv"
                if worldsafar:
                    adv = "wa"
            ship = "ai-" + ship_type + adv
            filepathShip = f"images/resources/components/basic_ships/{ship}.png"
            ship_image = self.use_image(filepathShip)
            context.paste(ship_image, (25 + x, 350), mask=ship_image)
            x += 145
        minorSpeciesSize = 670
        heightSpecies = 0
        if len(self.gamestate.get("minor_species", [])) > 0:
            heightSpecies=250
            text_drawable_image.text((640, 0), "Minor Species:", (255, 255, 255), font=font,
                                     stroke_width=stroke_width, stroke_fill=stroke_color)
            minor_species = self.gamestate["minor_species"]
            count = 0
            for species in minor_species:
                tile_image = Image.open("images/resources/components/minor_species/minorspecies_" +
                                        f"{species.replace(' ', '_').lower()}.png").convert("RGBA").resize((100, 100))
                context.paste(tile_image, (660 + 120 * count, 85), mask=tile_image)
                count += 1
        turnOrder = self.display_turn_order()
        context.paste(turnOrder, (640, heightSpecies),mask=turnOrder)
        text_drawable_image.text((630 +minorSpeciesSize, 0), "Parts Reference:", (255, 255, 255), font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        filepathRef = "images/resources/components/reference_sheets/upgrade_reference1.png"
        ref_image = self.use_image(filepathRef)
        context.paste(ref_image, (660+minorSpeciesSize, 80), mask=ref_image)
        filepathRef = "images/resources/components/reference_sheets/upgrade_reference2.png"
        ref_image = self.use_image(filepathRef)
        context.paste(ref_image, (970+minorSpeciesSize, 85), mask=ref_image)

        

        return context

    def getPlayerObjectFromColor(self, color):
        for i in self.gamestate["players"]:
            if self.gamestate["players"][i]["color"] == color:
                return self.gamestate["players"][i]

    def display_cube_track_reference(self, player):
        context = Image.new("RGBA", (1690, 125), (0, 0, 0, 0))

        spaces = [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
        pop_path = f"images/resources/components/all_boards/popcube_{player['color']}.png"

        font = ImageFont.truetype("images/resources/arial.ttf", size=50)
        stroke_color = (0, 0, 0)

        if player['color'] == "purple" or player['color'] == "blue":
            color = (255, 255, 255)
        else:
            color = (0, 0, 0)
        stroke_width = 1
        # pop_image = self.use_image(pop_path).resize((220, 75))
        # context.paste(pop_image, (0, 25), mask=pop_image)
        # text_drawable_image = ImageDraw.Draw(context)
        # text_drawable_image.text((18, 35), "Income:", color, font=font,
        #                          stroke_width=stroke_width, stroke_fill=stroke_color)
        # Resource details: [(image_path, text_color, player_key, amount_key)]
        resources = [
            ("images/resources/components/resourcesymbols/money.png",
             "images/resources/components/all_boards/popcube_orange.png",
             "money_pop_cubes", (-10, 0)),
            ("images/resources/components/resourcesymbols/material.png",
             "images/resources/components/all_boards/mats_brown.png",
             "material_pop_cubes", (20, 0)),
             ("images/resources/components/resourcesymbols/science.png",
             "images/resources/components/all_boards/science_pink.png",
             "science_pop_cubes", (50, 0))
        ]
        draw = ImageDraw.Draw(context)  
        def draw_resourceCube(context, pop_path, amount_key):
            population_track = player["population_track"]
            amount_index = player[amount_key] - 1
            if 0 <= amount_index < len(population_track):
                population_value = population_track[amount_index]
            else:
                population_value = 2
            ind = spaces.index(population_value) + 1
            x= 1315 - 106 * ind
            y = 18
            box_size = 100
            border = 10
            bordercolor = (150, 75, 0, 255)
            if "orange" in pop_path:
                border = 15
                bordercolor = (255, 215, 0, 255)
            if "pink" in pop_path:
                border = 5
                bordercolor = (255, 192, 203, 255)
            #context.paste(pop_image, (x,y))
            draw.rectangle([x, y, x+box_size, y+box_size],   
                            outline=bordercolor,   
                            width=border) 

        def draw_resource(context, img_path, amount_key, position):
            image = self.use_image(img_path).resize((30, 30))
            population_track = player["population_track"]
            amount_index = player[amount_key] - 1
            if 0 <= amount_index < len(population_track):
                population_value = population_track[amount_index]
            else:
                population_value = 2
            ind = spaces.index(population_value) + 1
            context.paste(image, (position[0] + 1330 - 106 * ind, position[1]))

        for img_path, color_path, amount_key, position in resources:
            draw_resourceCube(context, color_path, amount_key)
        for img_path, color_path, amount_key, position in resources:
            draw_resource(context, img_path, amount_key, position)

        # pop_image = self.use_image(pop_path).resize((75, 75))
        # for count, num in enumerate(spaces):
        #     x = 1310 - 90 * count
        #     context.paste(pop_image, (x, 25), mask=pop_image)
        #     mod = 0
        #     if num > 9:
        #         mod = 12
        #     text_drawable_image.text((x + 20 - mod, 35), str(num), color, font=font,
        #                              stroke_width=stroke_width, stroke_fill=stroke_color)
        return context


    def display_upkeep_track_reference(self, player):
        context = Image.new("RGBA", (1890, 145), (0, 0, 0, 0))
        draw = ImageDraw.Draw(context)  
        influenceTrack = [0,0,1,2,3,5,7,10,13,17,21,25,30]
        inf_path = "images/resources/components/all_boards/influence_disc_" + player["color"] + ".png"
        font = ImageFont.truetype("images/resources/arial.ttf", size=50)



        radius = 59
        border_width = 0  
        spacing = 2
        diameter = 2 * radius 
        discs = player["influence_discs"]

        inf_image = self.use_image(inf_path).resize((diameter-1,diameter-1))
        for count, num in enumerate(influenceTrack):
            x = 296+spacing + count * (diameter-14 + spacing)  
            y = 80 
            number = str(num)   
            text_bbox = draw.textbbox((0,0), number, font=font)  
            text_width = text_bbox[2] - text_bbox[0]  
            text_height = text_bbox[3] - text_bbox[1]  
            text_x = x - text_width // 2  
            text_y = y - text_height // 2  
            if 13-discs-1 < count:
                context.paste(inf_image,(x-radius,y-radius),mask=inf_image)
                draw.text((text_x, text_y-10), number, fill=(255,255,255,255), font=font)
        return context

    @staticmethod
    def getShipFullName(shipAbbreviation):
        if shipAbbreviation == "int":
            return "interceptor"
        elif shipAbbreviation == "cru":
            return "cruiser"
        elif shipAbbreviation == "drd":
            return "dreadnought"
        elif shipAbbreviation == "sb":
            return "starbase"
        elif shipAbbreviation == "orb":
            return "orbital"
        elif shipAbbreviation == "mon":
            return "monolith"
        else:
            return shipAbbreviation

    def draw_square_boxes(self, values):  
        box_size = 100  
        border_width = 10  
        spacing = 10  
        rows, cols = 3, 7  
        
        width = (box_size + spacing) * cols + spacing  
        height = (box_size + spacing) * rows + spacing  
        
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))  
        draw = ImageDraw.Draw(image)  

        font = ImageFont.truetype("arial.ttf", 50)  
        
        for row in range(rows):  
            for col in range(cols):  
                x = spacing + col * (box_size + spacing)  
                y = spacing + row * (box_size + spacing)  

                draw.rectangle([x, y, x+box_size, y+box_size],   
                            outline=(255,255,255,255),   
                            width=border_width)  
                value_index =  col  
                if value_index < len(values):  
                    number = str(values[value_index])   
                    text_bbox = draw.textbbox((0,0), number, font=font)  
                    text_width = text_bbox[2] - text_bbox[0]  
                    text_height = text_bbox[3] - text_bbox[1]  
                    text_x = x + (box_size - text_width) // 2  
                    text_y = y + (box_size - text_height) // 2  
                    
                    draw.text((text_x, text_y), number, fill=(255,255,255,255), font=font)  
        
        return image  

    def player_area(self, player):
        
        faction = self.get_short_faction_name(player["name"])
        context = Image.new("RGBA", (5000, 800), (0, 0, 0, 255))
        layout_path = f"images/resources/components/layouts/player_layout.png"
        layout_image = self.use_image(layout_path)
        context.paste(layout_image, (0,0))
        referenceX = 140
        border = 5
        pop_path = f"images/resources/components/all_boards/popcube_{player['color']}.png"
        pop_image = self.use_image(pop_path)
        pop_image = pop_image.crop((32, 32, pop_image.width - 32, pop_image.height - 32))
        imageSize = 100
        pop_image = pop_image.resize((imageSize, imageSize))
        context.paste(pop_image, (referenceX+10, 150), mask=pop_image)
        face_tile_path = f"images/resources/components/layouts/factionImages/{faction}_image.png"
        face_tile_image = self.use_image(face_tile_path)
        #face_tile_image = face_tile_image.crop((49, 252, 154, 357))
        face_tile_image = face_tile_image.resize((imageSize - 2 * border, imageSize - 2 * border))
        context.paste(face_tile_image, (referenceX + border+10, 150 + border), mask=face_tile_image)


       
        if "username" in player:
            font = ImageFont.truetype("images/resources/arial.ttf", size=50)
            stroke_color = (0, 0, 0)
            color = (255, 255, 255)
            stroke_width = 5
            text_drawable_image = ImageDraw.Draw(context)
            username = player["username"]
            if player.get("traitor"):
                text_drawable_image.text((10, 320), "TRAITOR", color, font=font,
                                        stroke_width=stroke_width, stroke_fill=stroke_color)
            text_drawable_image.text((10, 260), username, color, font=font,
                                        stroke_width=stroke_width, stroke_fill=stroke_color)
        

        
        if "disc_tiles_for_points" in player:
            discTile = Image.open("images/resources/components/discovery_tiles/discovery_2ptback.png")
            discTile = discTile.convert("RGBA").rotate(315, expand=True).resize((80, 80))
            for discT in range(player["disc_tiles_for_points"]):
                context.paste(discTile, (10 + 30 * discT, 370), mask=discTile)

        font = ImageFont.truetype("images/resources/arial.ttf", size=90)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        textHeightForP = 670
        text_drawable = ImageDraw.Draw(context)
        if player.get("passed"):
            text_drawable.text((10, textHeightForP), "Passed", fill=(255, 0, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)
        if player.get("eliminated"):
            text_drawable.text((10, textHeightForP), "Eliminated", fill=(255, 0, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)
        colorActive = "nada"
        if "activePlayerColor" in self.gamestate:
            colorActive = self.gamestate.get("activePlayerColor")
        if player["color"] in colorActive:
            text_drawable.text((10, textHeightForP), "Active", fill=(0, 255, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)

        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        listOfAncient = player["ancient_parts"]
        if "discoveryTileBonusPointTiles" in player:
            listOfAncient = listOfAncient + player["discoveryTileBonusPointTiles"]
        newX = 500
        for part in listOfAncient:
            discName = discTile_data[part]["name"]
            part_path = ("images/resources/components/discovery_tiles/discovery"
                         f"_{discName.replace(' ', '_').lower()}.png")
            part_image = self.use_image(part_path).resize((80, 80))
            context.paste(part_image, (newX, 700), mask=part_image)
            newX += 85
        title_path = f"images/resources/components/layouts/faction_titles/name_trade_{faction}.png"
        title_image = self.use_image(title_path)
        context.paste(title_image, (0,50))

        publicPoints = self.get_public_points(player,False)
        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=60)
        stroke_color = (0, 0, 0)
        color = (0, 0, 0)
        stroke_width = 2
        letX = referenceX - 75
        if publicPoints > 9:
            letX = letX -15
        text_drawable_image.text((letX, 165), str(publicPoints), color, font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)
        
        colonyPath = "images/resources/components/all_boards/colony_ship.png"
        colonyShip = self.use_image(colonyPath)

        for i in range(player["colony_ships"]):
            context.paste(colonyShip, (referenceX+145+ 90 * i, 155), colonyShip)


        
        resources = [
             ("images/resources/components/resourcesymbols/material.png",
             (101, 67, 33), "materials", "material_pop_cubes"),
            ("images/resources/components/resourcesymbols/money.png",
             (255, 255, 0), "money", "money_pop_cubes"),
            ("images/resources/components/resourcesymbols/science.png",
             (255, 192, 203), "science", "science_pop_cubes")
           
        ]
        font = ImageFont.truetype("images/resources/arial.ttf", size=70)
        stroke_color = (255, 255, 255)
        stroke_width = 1
        def draw_resource(context, img_path, color, player_key, amount_key, position):
            buffer = 0
            if player[player_key] < 10:
                buffer = 20
            text_drawable_image.text((position[0] + buffer, position[1]), f"{player[player_key]}", color, font=font,
                                     stroke_width=stroke_width, stroke_fill=stroke_color)

        y=390
        referenceX = 280
        for img_path, text_color, player_key, amount_key in resources:
            draw_resource(context, img_path, text_color, player_key, amount_key, (referenceX, y))
            referenceX += 110


        sizeOfTech = 210
        referenceX = 750
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        def process_tech(tech_list, tech_type, start_y):
            for counter, tech in enumerate(tech_list):
                tech_details = tech_data.get(tech)
                techName = tech_details["name"].lower().replace(" ", "_") if tech_details else tech
                tech_path = f"images/resources/components/technology/{tech_type}/tech_{techName}.png"
                if not os.path.exists(tech_path):
                    tech_path = f"images/resources/components/technology/rare/tech_{techName}.png"
                #tech_image = self.use_image(tech_path)
                tech_image = self.use_image(tech_path)
                context.paste(tech_image, (referenceX + 196 * counter+30, start_y+8), mask=tech_image)
        process_tech(player["nano_tech"], "nano", sizeOfTech*2+35)
        process_tech(player["grid_tech"], "grid", sizeOfTech+30)
        process_tech(player["military_tech"], "military", 20)
        context3 = self.display_upkeep_track_reference(player)
        context.paste(context3, (2130, 643), mask=context3)
        context2 = self.display_cube_track_reference(player)
        context.paste(context2, (2438, 500),mask=context2)

        inf_path = "images/resources/components/all_boards/influence_disc_" + player["color"] + ".png"
        inf_image = self.use_image(inf_path).resize((120, 120))
        text_drawable_image = ImageDraw.Draw(context)
        
        stroke_color = (0, 0, 0)
        color = (255, 255, 255)
        stroke_width = 2
        for x, action in enumerate(["explore", "research", "upgrade", "build", "move", "influence"]):
            if f"{action}_action_counters" in player:
                num = player[f"{action}_action_counters"]
                if num > 0:
                    context.paste(inf_image, (34 + int(116 * x), 470), mask=inf_image)
                if num > 1:
                    font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                    text_drawable_image.text((70 + int(116 * x), 500), f"x{num}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            action_activation = player[f"{action}_apt"]
            font = ImageFont.truetype("images/resources/arial.ttf", size=35)
            text_drawable_image.text((50 + int(116 * x), 607), f"{action_activation}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
        font = ImageFont.truetype("images/resources/arial.ttf", size=35)
        if "magellan" in faction:
            text_drawable_image.text((618, 417), f"1", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
        else:
            text_drawable_image.text((618, 417), f"2", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            





        reputation_path = "images/resources/components/all_boards/reputation.png"
        amb_empty_path = "images/resources/components/layouts/ambassador_only_empty.png"
        mixed_empty_path = "images/resources/components/layouts/mixed_empty.png"
        reputation_image = self.use_image(reputation_path)
        amb_empty_image = self.use_image(amb_empty_path).resize((120,120))
        mixed_empty_image = self.use_image(mixed_empty_path).resize((120,120))
        reputationX = 3850
        for x, reputation in enumerate(player["reputation_track"]):
            if isinstance(reputation, int) or "mixed" in reputation:
                context.paste(mixed_empty_image, (reputationX+x*150, 600), mask=mixed_empty_image)
            else:
                context.paste(amb_empty_image, (reputationX+x*150, 600), mask=amb_empty_image)
            if isinstance(reputation, int):
                if "gameEnded" in self.gamestate:
                    pointsPath = "images/resources/components/all_boards/points.png"
                    points = self.use_image(pointsPath).resize(((120,120)))
                    context.paste(points, (reputationX+x*150, 600), mask=points)
                    font = ImageFont.truetype("images/resources/arial.ttf", size=90)
                    stroke_color = (0, 0, 0)
                    color = (0, 0, 0)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context)
                    text_drawable_image.text((reputationX+x*150+30, 600), str(reputation), color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
                else:
                    context.paste(reputation_image, (reputationX+x*150, 600), mask=reputation_image)
            if not isinstance(reputation, int) and "-" in reputation:
                faction = reputation.split("-")[1]
                color = reputation.split("-")[2]

                if faction == "minor":
                    amb_tile_path = ("images/resources/components/minor_species/minorspecies_"
                                     f"{color.replace(' ', '_').lower()}.png")
                    amb_tile_image = self.use_image(amb_tile_path).resize((110,110))
                else:
                    amb_tile_path = f"images/resources/components/factions/{faction}_ambassador.png"
                    amb_tile_image = self.use_image(amb_tile_path).resize((110,110))
                context.paste(amb_tile_image, (reputationX+x*150, 600), mask=amb_tile_image)
                if faction != "minor" or "cube" in color:
                    if "cube" in color:
                        color = player["color"]
                    pop_path = f"images/resources/components/all_boards/popcube_{color}.png"
                    pop_image = self.use_image(pop_path).resize((42,42))
                    context.paste(pop_image, (reputationX+x*150+30, 600+60), mask=pop_image)


        faction = self.get_short_faction_name(player["name"])
        ships = ["int", "cru", "drd", "sb","orb"]
        stroke_color = (0, 0, 0)
        color = (255, 255, 255)
        stroke_width = 2
        font = ImageFont.truetype("images/resources/arial.ttf", size=35)
        for counter, ship in enumerate(ships):
            shipFullName = self.getShipFullName(ship)
            if ship == "orb" and faction != "exile":
                continue
            ship_blueprint_path = f"images/resources/components/layouts/blueprints/blueprint_{shipFullName}.png"
            if faction == "planta":
                ship_blueprint_path = ship_blueprint_path.replace(".png","_planta.png")
            ship_blueprint = self.use_image(ship_blueprint_path)
            if ship == "drd":
                #ship_blueprint = ship_blueprint.resize((561,400))
                if faction == "rho":
                    continue
            #else:
                #ship_blueprint = ship_blueprint.resize((424,400))
            mod = 0
            if ship == "sb" and faction == "exile":
                continue
            if ship =="sb" or ship =="orb":
                mod = 161
                if ship == "orb":
                    mod = -389
            context.paste(ship_blueprint, (2250 + 550 * counter+mod, 70))
            shipMod = PlayerShip(player, shipFullName)
            total_energy = shipMod.total_energy
            usedEnergy = total_energy - shipMod.energy
            speed = str(shipMod.speed)
            drive = str(shipMod.range)
            hull = str(shipMod.hull)
            computer = str(shipMod.computer)
            shield = str(shipMod.shield)
            cost = str(shipMod.cost)
            text_drawable_image.text((2250 + 550 * counter+mod+40, 70+42), f"{usedEnergy}/{total_energy}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            if drive != "0":
                text_drawable_image.text((2250 + 550 * counter+mod+155, 70+42), f"{drive}", color, font=font,
                                                stroke_width=stroke_width, stroke_fill=stroke_color)

            text_drawable_image.text((2250 + 550 * counter+mod+230, 70+42), f"{hull}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            text_drawable_image.text((2250 + 550 * counter+mod+295, 70+42), f"{computer}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            text_drawable_image.text((2250 + 550 * counter+mod+375, 70+42), f"{shield}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            text_drawable_image.text((2250 + 550 * counter+mod+375, 68), f"{speed}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            if ship =="drd":
                mod += 5
            text_drawable_image.text((2250 + 550 * counter+mod+10, 70), f"{cost}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
            shortF = faction
            if "terran" in shortF:
                shortF = "terran"
            shipClassPath = f"images/resources/components/layouts/blueprints/classes/{shortF}_{shipFullName}_class.png"
            shipClass = self.use_image(shipClassPath)
            context.paste(shipClass, (2250 + 550 * counter+mod+175, 74))


            if ship != "orb":
                filepath = f"images/resources/components/fancy_ships/fancy_{player['color']}-{ship}.png"
                if self.gamestate.get("fancy_ships") and os.path.exists(filepath):
                    filepath = f"images/resources/components/fancy_ships/fancy_{player['color']}-{ship}.png"
                else:
                    filepath = f"images/resources/components/basic_ships/{player['color']}-{ship}.png"
                ship_image = self.use_image(filepath).resize((120, 120))
                if ship == "drd":
                    ship_image = ship_image.rotate(270,expand=True)
                for shipCounter in range(player["ship_stock"][counter]):
                    mod = 0
                    if ship == "drd" or ship =="sb":
                        mod = 161
                        
                    context.paste(ship_image, (2670 + 550 * counter+mod, 150+35 * shipCounter), ship_image)



        
        interceptCoord = [(78, 39), (20, 87), (78, 97), (136, 87), (148, 39)]
        cruiserCoord = [(215, 58), (271, 44), (328, 58), (215, 116), (271, 102), (328, 116), (388, 10)]
        dreadCoord = [(435, 58), (492, 44), (550, 44), (607, 58), (435, 116),
                        (492, 102), (550, 102), (607, 116), (628, 15)]
        if faction == "exile":
            orbCoord = [(764, 68), (821, 40), (706, 97), (816, 100)]
        sbCoord = [(705, 39), (821, 39), (705, 97), (763, 60), (821, 97), (815, 0)]

        if player["name"] == "Planta":
            interceptCoord.pop(2)
            cruiserCoord.pop(3)
            dreadCoord.pop(4)
            sbCoord.pop(2)

        with open("data/parts.json", "r") as f:
            part_data = json.load(f)

        def process_parts(parts, coords, refX, square_size, shipType):
            for counter, part in enumerate(parts):
                if part == "empty":
                    continue
                part_details = part_data.get(part)  
                partName = part_details["name"].lower().replace(" ", "_") if part_details else part  
                part_path = f"images/resources/components/upgrades/{partName}.png"  
                part_image = self.use_image(part_path).resize((square_size,square_size+8))  
                if part == "mus":  
                    part_image = part_image.resize((int(square_size * 0.69), int(square_size * 0.69)))  
                
                # Scale coordinates based on square size, original square was 58  
                x, y = coords[counter]  
                if shipType == "interceptor":
                    y+=8
                    x-=5
                elif shipType == "cruiser":
                    x+= 35
                elif shipType == "dreadnought":
                    x += 47
                else:
                    x +=78
                    y+=8
                scaled_x = refX + int(x * square_size / 58)  
                scaled_y = int(y * square_size / 58)  
                
                # Paste the image  
                context.paste(part_image, (scaled_x, scaled_y+50), mask=part_image)  
        referenceX = 2220
        sizeOfSquare = 137
        process_parts(player["interceptor_parts"], interceptCoord, referenceX,sizeOfSquare,"interceptor")
        process_parts(player["cruiser_parts"], cruiserCoord,referenceX,sizeOfSquare,"cruiser")
        process_parts(player["dread_parts"], dreadCoord,referenceX,sizeOfSquare,"dreadnought")
        if faction == "exile":
            process_parts(player["orb_parts"], orbCoord,referenceX,sizeOfSquare,"orbital")
        else:
            process_parts(player["starbase_parts"], sbCoord,referenceX,sizeOfSquare,"starbase")

        if "shrine_in_storage" in player:
            shrine_board_path = "images/resources/components/factions/shrine_board.png"
            shrine_board_image = self.use_image(shrine_board_path)
            context.paste(shrine_board_image, (4600, 50))
            shrine_path = "images/resources/components/factions/shrine.png"
            shrine_image = self.use_image(shrine_path)
            for shrineCount, val in enumerate(player["shrine_in_storage"]):
                place = shrineCount
                widthOfShrine = 24*2
                xspacing = 23*2
                yspacing = 28*2
                xLoc = 4600+place % 3 * (xspacing + widthOfShrine)
                yLoc = place // 3 * (yspacing + widthOfShrine)
                if val == 1:
                    context.paste(shrine_image, (50 + xLoc, 96+ yLoc))


        return context



        

    def player_area_old(self, player):
        faction = self.get_short_faction_name(player["name"])
        filepath = "images/resources/components/factions/" + str(faction) + "_board.png"
        context = Image.new("RGBA", (1440, 625), (0, 0, 0, 255))
        board_image = self.use_image(filepath)
        context.paste(board_image, (0, 0))
        inf_path = "images/resources/components/all_boards/influence_disc_" + player["color"] + ".png"
        inf_image = self.use_image(inf_path).resize((40, 40))
        with open("data/parts.json", "r") as f:
            part_data = json.load(f)

        for x in range(player["influence_discs"]):
            context.paste(inf_image, (764 - int(38.5 * x), 450), mask=inf_image)

        for x, action in enumerate(["explore", "research", "upgrade", "build", "move", "influence"]):
            if f"{action}_action_counters" in player:
                num = player[f"{action}_action_counters"]
                if num > 0:
                    context.paste(inf_image, (12 + int(47 * x), 422), mask=inf_image)
                if num > 1:
                    font = ImageFont.truetype("images/resources/arial.ttf", size=25)
                    stroke_color = (0, 0, 0)
                    color = (255, 255, 255)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context)
                    text_drawable_image.text((17 + int(47 * x), 426), f"x{num}", color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
        if "shrine_in_storage" in player:
            shrine_board_path = "images/resources/components/factions/shrine_board.png"
            shrine_board_image = self.use_image(shrine_board_path)
            context.paste(shrine_board_image, (50, 240))
            shrine_path = "images/resources/components/factions/shrine.png"
            shrine_image = self.use_image(shrine_path)
            for shrineCount, val in enumerate(player["shrine_in_storage"]):
                place = shrineCount
                widthOfShrine = 24
                xspacing = 23
                yspacing = 28
                xLoc = place % 3 * (xspacing + widthOfShrine)
                yLoc = place // 3 * (yspacing + widthOfShrine)
                if val == 1:
                    context.paste(shrine_image, (76 + xLoc, 265 + yLoc))
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)

        def process_tech(tech_list, tech_type, start_y):
            for counter, tech in enumerate(tech_list):
                tech_details = tech_data.get(tech)
                techName = tech_details["name"].lower().replace(" ", "_") if tech_details else tech
                tech_path = f"images/resources/components/technology/{tech_type}/tech_{techName}.png"
                if not os.path.exists(tech_path):
                    tech_path = f"images/resources/components/technology/rare/tech_{techName}.png"
                tech_image = self.use_image(tech_path)
                context.paste(tech_image, (299 + 71 * counter, start_y), mask=tech_image)
                # if part_data.get(tech, {}).get("nrg_use", 0) > 0:
                #     energy_image = self.use_image("images/resources/components/energy/" +
                #                                   f"{str(part_data[tech]['nrg_use'])}energy.png").resize((18, 38))
                #     context.paste(energy_image, (299 + 71 * counter + 50, start_y + 8), mask=energy_image)

        process_tech(player["nano_tech"], "nano", 360)
        process_tech(player["grid_tech"], "grid", 285)
        process_tech(player["military_tech"], "military", 203)

        if faction == "rho":
            # Last coord is for muon source exclusively
            interceptCoord = [(152, 39), (94, 86), (152, 97), (210, 86), (226, 39)]
            cruiserCoord = [(360, 63), (418, 39), (476, 63), (360, 121), (418, 97), (476, 121), (492, 19)]
            dreadCoord = [(435, 64), (493, 40), (551, 40), (609, 64), (435, 122),
                          (493, 98), (551, 98), (609, 122), (628, 20)]
            sbCoord = [(621, 39), (737, 39), (620, 97), (679, 66), (736, 97), (741, 0)]
        else:
            interceptCoord = [(74, 39), (16, 86), (74, 97), (132, 86), (148, 39)]
            cruiserCoord = [(221, 63), (279, 39), (337, 63), (221, 121), (279, 97), (337, 121), (353, 19)]
            dreadCoord = [(435, 64), (493, 40), (551, 40), (609, 64), (435, 122),
                          (493, 98), (551, 98), (609, 122), (628, 20)]
            if faction == "exile":
                orbCoord = [(753, 68), (810, 40), (694, 97), (811, 100)]
            sbCoord = [(697, 39), (813, 39), (697, 97), (755, 66), (814, 97), (815, 0)]

        if player["name"] == "Planta":
            interceptCoord.pop(2)
            cruiserCoord.pop(3)
            dreadCoord.pop(4)
            sbCoord.pop(2)

        with open("data/parts.json", "r") as f:
            part_data = json.load(f)

        def process_parts(parts, coords):
            for counter, part in enumerate(parts):
                if part == "empty":
                    continue
                part_details = part_data.get(part)
                partName = part_details["name"].lower().replace(" ", "_") if part_details else part
                part_path = f"images/resources/components/upgrades/{partName}.png"
                part_image = self.use_image(part_path)
                if part == "mus":
                    part_image = part_image.resize((40, 40))
                context.paste(part_image, coords[counter], mask=part_image)

        process_parts(player["interceptor_parts"], interceptCoord)
        process_parts(player["cruiser_parts"], cruiserCoord)
        process_parts(player["dread_parts"], dreadCoord)
        if faction == "exile":
            process_parts(player["orb_parts"], orbCoord)
        else:
            process_parts(player["starbase_parts"], sbCoord)

        reputation_path = "images/resources/components/all_boards/reputation.png"
        reputation_image = self.use_image(reputation_path)
        mod = 0
        scaler = 86
        if len(player["reputation_track"]) > 4:
            scaler = 67
            mod = 3
        for x, reputation in enumerate(player["reputation_track"]):
            if isinstance(reputation, int):
                if "gameEnded" in self.gamestate:
                    pointsPath = "images/resources/components/all_boards/points.png"
                    points = self.use_image(pointsPath).resize(((58, 58)))
                    context.paste(points, (825, 172 + x * scaler - mod), mask=points)
                    font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                    stroke_color = (0, 0, 0)
                    color = (0, 0, 0)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context)
                    text_drawable_image.text((825 + 13, 172 + x * scaler - mod), str(reputation), color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
                else:
                    context.paste(reputation_image, (825, 172 + x * scaler - mod), mask=reputation_image)
            if not isinstance(reputation, int) and "-" in reputation:
                faction = reputation.split("-")[1]
                color = reputation.split("-")[2]

                if faction == "minor":
                    amb_tile_path = ("images/resources/components/minor_species/minorspecies_"
                                     f"{color.replace(' ', '_').lower()}.png")
                    amb_tile_image = self.use_image(amb_tile_path)
                else:
                    amb_tile_path = f"images/resources/components/factions/{faction}_ambassador.png"
                    amb_tile_image = self.use_image(amb_tile_path)
                context.paste(amb_tile_image, (825, 172 + x * scaler - mod), mask=amb_tile_image)
                if faction != "minor" or "cube" in color:
                    if "cube" in color:
                        color = player["color"]
                    pop_path = f"images/resources/components/all_boards/popcube_{color}.png"
                    pop_image = self.use_image(pop_path).resize((35, 35))
                    context.paste(pop_image, (825 + 20, 172 + x * scaler + 25 - mod), mask=pop_image)

        x = 925
        y = 0
        font = ImageFont.truetype("images/resources/arial.ttf", size=90)
        stroke_color = (0, 0, 0)
        stroke_width = 2

        if player.get("passed"):
            text_image = Image.new('RGBA', (500, 500), (0, 0, 0, 0))
            text_drawable = ImageDraw.Draw(text_image)
            text_drawable.text((0, 50), "Passed", fill=(255, 0, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)
            text_image = text_image.rotate(45, expand=True)
            context.paste(text_image, (0, 500), text_image)
        
        if player.get("eliminated"):
            text_image = Image.new('RGBA', (500, 500), (0, 0, 0, 0))
            text_drawable = ImageDraw.Draw(text_image)
            text_drawable.text((0, 50), "Eliminated", fill=(255, 0, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)
            text_image = text_image.rotate(45, expand=True)
            context.paste(text_image, (0, 500), text_image)
        colorActive = "nada"
        if "activePlayerColor" in self.gamestate:
            colorActive = self.gamestate.get("activePlayerColor")
        if player["color"] == colorActive:
            text_image = Image.new('RGBA', (500, 500), (0, 0, 0, 0))
            text_drawable = ImageDraw.Draw(text_image)
            text_drawable.text((0, 50), "Active", fill=(0, 255, 0), font=font,
                               stroke_width=stroke_width, stroke_fill=stroke_color)
            text_image = text_image.rotate(45, expand=True)
            context.paste(text_image, (0, 500), text_image)
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)

        # Resource details: [(image_path, text_color, player_key, amount_key)]
        resources = [
            ("images/resources/components/resourcesymbols/money.png",
             (255, 255, 0), "money", "money_pop_cubes"),
            ("images/resources/components/resourcesymbols/science.png",
             (255, 192, 203), "science", "science_pop_cubes"),
            ("images/resources/components/resourcesymbols/material.png",
             (101, 67, 33), "materials", "material_pop_cubes")
        ]

        def draw_resource(context, img_path, color, player_key, amount_key, position):
            image = self.use_image(img_path)
            context.paste(image, position)
            text_drawable_image = ImageDraw.Draw(context)
            text_drawable_image.text((position[0] + 120, position[1]), f"{player[player_key]}", color, font=font,
                                     stroke_width=stroke_width, stroke_fill=stroke_color)

        newY = y
        newX = x + 240
        

        listOfAncient = player["ancient_parts"]
        if "discoveryTileBonusPointTiles" in player:
            listOfAncient = listOfAncient + player["discoveryTileBonusPointTiles"]
        for part in listOfAncient:
            discName = discTile_data[part]["name"]
            part_path = ("images/resources/components/discovery_tiles/discovery"
                         f"_{discName.replace(' ', '_').lower()}.png")
            part_image = self.use_image(part_path).resize((80, 80))
            context.paste(part_image, (newX, newY), mask=part_image)
            newY += 85
        for img_path, text_color, player_key, amount_key in resources:
            draw_resource(context, img_path, text_color, player_key, amount_key, (x, y))
            y += 100
        colonyPath = "images/resources/components/all_boards/colony_ship.png"
        colonyShip = self.use_image(colonyPath)

        for i in range(player["colony_ships"]):
            context.paste(colonyShip, (x + 50 * i, y + 10), colonyShip)

        publicPoints = self.get_public_points(player,False)
        pointsPath = "images/resources/components/all_boards/points.png"
        points = self.use_image(pointsPath)
        context.paste(points, (x + 250, y + 10), points)
        font = ImageFont.truetype("images/resources/arial.ttf", size=50)
        stroke_color = (0, 0, 0)
        color = (0, 0, 0)
        stroke_width = 2
        text_drawable_image = ImageDraw.Draw(context)
        letX = x + 250 + 25
        if publicPoints > 9:
            letX = x + 250 + 12
        text_drawable_image.text((letX, y + 21), str(publicPoints), color, font=font,
                                 stroke_width=stroke_width, stroke_fill=stroke_color)

        y += 90
        ships = ["int", "cru", "drd", "sb"]
        ultimateC = 0
        for counter, ship in enumerate(ships):
            filepath = f"images/resources/components/fancy_ships/fancy_{player['color']}-{ship}.png"
            if self.gamestate.get("fancy_ships") and os.path.exists(filepath):
                filepath = f"images/resources/components/fancy_ships/fancy_{player['color']}-{ship}.png"
            else:
                filepath = f"images/resources/components/basic_ships/{player['color']}-{ship}.png"
            ship_image = self.use_image(filepath).resize((80, 80))
            for shipCounter in range(player["ship_stock"][counter]):
                context.paste(ship_image, (x + 10 * ultimateC + 70 * counter, y), ship_image)
                ultimateC += 1

        discTile = Image.open("images/resources/components/discovery_tiles/discovery_2ptback.png")
        discTile = discTile.convert("RGBA").resize((40, 40))
        discTile = discTile.rotate(315, expand=True).resize((80, 80))
        if "disc_tiles_for_points" in player:
            for discT in range(player["disc_tiles_for_points"]):
                context.paste(discTile, (x + 25 * discT, y + 50), mask=discTile)

        context2 = self.display_cube_track_reference(player)
        context.paste(context2, (0, 500))
        return context

    def get_public_points(self, player, showPrivateRegardless:bool):
        points = 0
        tile_map = self.gamestate["board"]
        color = player["color"]
        for tile in tile_map:
            if tile_map[tile].get("owner") == color:
                points += tile_map[tile]["vp"]
                if "Lyra" in player["name"] and "shrines" in tile_map[tile]:
                    points += tile_map[tile]["shrines"]
                if player["name"] == "The Exiles" and tile_map[tile].get("orbital_pop", [0])[0] == 1:
                    points += 1
                if "warpPoint" in tile_map[tile]:
                    points += tile_map[tile]["warpPoint"]
                if "warpDisc" in tile_map[tile]:
                    points += tile_map[tile]["warpDisc"]
                if all(["art" in player.get("discoveryTileBonusPointTiles", []),
                        tile_map[tile]["artifact"] == 1]):
                    points += 1
                if "player_ships" in tile_map[tile]:
                    for ship in tile_map[tile]["player_ships"]:
                        if "mon" in ship:
                            points += 3
                if player["name"] == "Planta":
                    points += 1
            if player["name"] == "Descendants of Draco" and "player_ships" in tile_map[tile]:
                for ship in tile_map[tile]["player_ships"]:
                    if "anc" in ship:
                        points += 1
        techTypes = ["military_tech", "grid_tech", "nano_tech"]
        for tType in techTypes:
            if len(player.get(tType, [])) > 3:
                if len(player[tType]) == 7:
                    points += 5
                else:
                    points += len(player[tType]) - 3
        if "disc_tiles_for_points" in player:
            points += player["disc_tiles_for_points"] * 2
        reputationPoints = 0
        ambass = 0
        repu = 0
        countAmb = False
        countRep = False
        for reputation in player["reputation_track"]:
            if isinstance(reputation, int):
                repu += 1
                if "gameEnded" in self.gamestate or showPrivateRegardless:
                    points += reputation
                    reputationPoints += reputation
            if not isinstance(reputation, int) and "-" in reputation:
                reputation = reputation.lower()
                points += 1
                ambass += 1
                if "three" in reputation:
                    points += 2
                if "per ambassador" in reputation:
                    countAmb = True
                if "per rep" in reputation:
                    countRep = True
        if countAmb:
            points += ambass
        if countRep:
            points += repu
        if "magPartPoints" in player:
            points += player["magPartPoints"]

        if "rep" in player.get("discoveryTileBonusPointTiles", []):
            points += reputationPoints // 3
        if player.get("traitor"):
            if player["name"] == "Rho Indi Syndicate":
                pass
            else:
                points -= 2
        return points

    def show_game(self):
        def load_tile_coordinates():
            configs = Properties()
            with open("data/tileImageCoordinates.properties", "rb") as f:
                configs.load(f)
            return configs

        def paste_tiles(context, tile_map, hyperlane, player_count):
            configs = load_tile_coordinates()
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            if hyperlane:
                hyperImage = self.use_image("images/resources/hexes/5playerhyperlane.png").resize((1125, 900))
                context.paste(hyperImage, (1820, 2850), mask=hyperImage)
                if player_count == 4:
                    hyperImageRot = self.use_image("images/resources/hexes/5playerhyperlane.png").resize((1125, 900)).rotate(180)
                    context.paste(hyperImageRot, (1560,1650), mask=hyperImageRot)
                min_x = min(min_x, 1560)
                min_y = min(min_y, 1650)
                max_x = max(max_x, 1820 + hyperImage.width)
                max_y = max(max_y, 2850 + hyperImage.height)
            for tile in tile_map:
                tile_image = self.board_tile_image(tile).resize((345, 300))
                x, y = map(int, configs.get(tile)[0].split(","))
                context.paste(tile_image, (x, y), mask=tile_image)
                # Update bounding box coordinates
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + tile_image.width)
                max_y = max(max_y, y + tile_image.height)
            return min_x, min_y, max_x, max_y
        context = Image.new("RGBA", (4160, 5100), (0, 0, 0, 255))
        hyperlane5 = False
        if self.gamestate.get("5playerhyperlane"):
            hyperlane5 = True
        min_x, min_y, max_x, max_y = paste_tiles(context, self.gamestate["board"], hyperlane5, self.gamestate["player_count"])
        cropped_context = context.crop((min_x, min_y, max_x, max_y))

        def create_player_area():
            pCount = len(self.gamestate["players"])
            pLength = 850
            player_area_length = pCount * pLength
            # if pCount > 6:
            #     player_area_length = 2250
            width = 5420 #if (pCount != 2 and pCount != 4) else 2980
            context2 = Image.new("RGBA", (width, player_area_length), (0, 0, 0, 255))
            x, y, count = 100, 50, 0
            for player in self.gamestate["players"]:
                player_image = self.player_area(self.gamestate["players"][player])
                # if "username" in self.gamestate["players"][player]:
                #     font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                #     stroke_color = (0, 0, 0)
                #     color = (255, 165, 0)
                #     stroke_width = 2
                #     text_drawable_image = ImageDraw.Draw(context2)
                #     username = self.gamestate["players"][player]["username"]

                #     if self.gamestate["players"][player].get("traitor"):
                #         username += " (TRAITOR)"
                #     text_drawable_image.text((x, y), username, color, font=font,
                #                              stroke_width=stroke_width, stroke_fill=stroke_color)
                context2.paste(player_image, (x, y), mask=player_image)
                y +=pLength
                #count += 1
                # if count % 2 == 0 and pCount == 4:
                #     x = 100
                #     y += 700
                # elif count % 3 == 0 and pCount != 4:
                #     x = 100
                #     y += 700
                # else:
                #     x += 1440
            return context2
        context2 = create_player_area()
        context3 = self.display_techs("Available Techs",self.gamestate["available_techs"])
        width = int(context3.size[0] * 500/context3.size[1])
        context3 = context3.resize((width, 500))
        context4 = self.display_remaining_tiles()
        context5 = self.display_remaining_discoveries()
        #context6 = self.display_turn_order()
        # context5 = self.display_cube_track_reference()
        pCount = len(self.gamestate["players"])
        width = 4150 if (pCount != 2 and pCount != 4) else 2800
        width = max([context2.size[0], context3.size[0] + context4.size[0] + 150,
                     cropped_context.size[0], context5.size[0]])
        height = (cropped_context.size[1] + context2.size[1] +
                  max(context3.size[1], context4.size[1]) + 90)
        final_context = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        centering = int((width - cropped_context.size[0])/2)
        final_context.paste(cropped_context, (centering, 0))
        #final_context.paste(context6, (0, 0))
        final_context.paste(context2, (0, cropped_context.size[1]+ max(context3.size[1],context4.size[1])))
        final_context.paste(context3, (0, cropped_context.size[1]))
        # final_context.paste(context5, (50, context2.size[1] - 20))
        final_context.paste(context4, (context3.size[0] + 150,
                                       cropped_context.size[1]))
        final_context.paste(context5,
                            (0, cropped_context.size[1] + context2.size[1] + max(context3.size[1],
                                                                                 context4.size[1])))
        bytes_io = BytesIO()
        final_context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="map_image.webp")

    async def show_map(self):
        def load_tile_coordinates():
            configs = Properties()
            with open("data/tileImageCoordinates.properties", "rb") as f:
                configs.load(f)
            return configs

        def paste_tiles(context, tile_map):
            configs = load_tile_coordinates()
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            for tile in tile_map:
                tile_image = self.board_tile_image(tile)
                x, y = map(int, configs.get(tile)[0].split(","))
                context.paste(tile_image, (x, y), mask=tile_image)
                # Update bounding box coordinates
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + tile_image.width)
                max_y = max(max_y, y + tile_image.height)
            return min_x, min_y, max_x, max_y
        context = Image.new("RGBA", (4160, 5100), (0, 0, 0, 255))
        min_x, min_y, max_x, max_y = paste_tiles(context, self.gamestate["board"])
        cropped_context = context.crop((min_x, min_y, max_x, max_y))
        # cropped_context=cropped_context.resize([int((max_x - min_x) / 2), int((max_y - min_y) / 2)])
        bytes_io = BytesIO()
        cropped_context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="map_image.webp")

    def get_file(self, imageName: str):
        bytes_io = BytesIO()
        image = self.use_image(imageName)
        image.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="image.webp")

    def append_images(self, images):
        image1 = images[0]
        context = Image.new("RGBA", ((image1.size[0] + 10) * len(images), image1.size[1]), (255, 255, 255, 0))
        for x, image in enumerate(images):
            context.paste(image, (x * (image1.size[0] + 10), 0), mask=image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="image.webp")

    async def show_stats(self):
        def create_player_area():
            pCount = len(self.gamestate["players"])
            player_area_length = 1500 if pCount > 3 else 750
            width = 4420 if (pCount != 2 and pCount != 4) else 2980
            context2 = Image.new("RGBA", (width, player_area_length), (0, 0, 0, 255))
            x, y, count = 100, 50, 0
            for player in self.gamestate["players"]:
                player_image = self.player_area(self.gamestate["players"][player])
                if "username" in self.gamestate["players"][player]:
                    font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                    stroke_color = (0, 0, 0)
                    color = (255, 165, 0)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context2)
                    username = self.gamestate["players"][player]["username"]

                    if self.gamestate["players"][player].get("traitor"):
                        username += " (TRAITOR)"
                    text_drawable_image.text((x, y), username, color, font=font,
                                             stroke_width=stroke_width, stroke_fill=stroke_color)
                context2.paste(player_image, (x, y + 50), mask=player_image)
                count += 1
                if count % 2 == 0 and pCount == 4:
                    x = 100
                    y += 700
                elif count % 3 == 0 and pCount != 4:
                    x = 100
                    y += 700
                else:
                    x += 1440
            return context2
        context2 = create_player_area()
        context3 = self.display_techs("Available Techs",self.gamestate["available_techs"])
        context4 = self.display_remaining_tiles()
        # context5 = self.display_cube_track_reference()
        pCount = len(self.gamestate["players"])
        width = 4150 if (pCount != 2 and pCount != 4) else 2800
        width = max(context2.size[0], context3.size[0] + context4.size[0] + 150)
        final_context = Image.new("RGBA",
                                  (width, context2.size[1] + max(context3.size[1], context4.size[1])),
                                  (0, 0, 0, 255))
        final_context.paste(context2, (0, 0))
        final_context.paste(context3, (0, context2.size[1]))
        # final_context.paste(context5, (50, context2.size[1] - 20))
        final_context.paste(context4, (context3.size[0] + 150, context2.size[1]))

        bytes_io = BytesIO()
        final_context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="stats_image.webp")

    def show_available_techs(self):
        context = self.display_techs("Available Techs",self.gamestate["available_techs"])
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)

        return discord.File(bytes_io, filename="techs_image.webp")
    

    def show_select_techs(self, message:str, techs):
        context = self.display_techs(message,techs)
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)

        return discord.File(bytes_io, filename="techs_image.webp")

    def show_single_tile(self, tile_image):
        mult = 1024 / 345
        context = Image.new("RGBA", (int(345 * mult), int(299 * mult)), (255, 255, 255, 0))
        context.paste(tile_image, (0, 0), mask=tile_image)
        byteData = BytesIO()
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="tile_image.webp")
        return file

    def show_minor_species(self):
        minor_species = self.gamestate["minor_species"]
        context = Image.new("RGBA", (300 * len(minor_species), 260), (255, 255, 255, 0))
        count = 0
        for species in minor_species:
            tile_image = Image.open("images/resources/components/minor_species/minorspecies_" +
                                    f"{species.replace(' ', '_').lower()}.png").convert("RGBA").resize((260, 260))
            context.paste(tile_image, (300 * count, 0), mask=tile_image)
            count += 1
        byteData = BytesIO()
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="disc_tile_image.webp")
        return file

    def show_shrine_board(self, player):
        context = Image.new("RGBA", (927, 847), (255, 255, 255, 0))

        shrine_board_path = "images/resources/components/factions/shrine_board.png"
        shrine_board_image = Image.open(shrine_board_path)
        context.paste(shrine_board_image, (0, 0))
        shrine_path = "images/resources/components/factions/shrine.png"
        shrine_image = Image.open(shrine_path).resize((119, 119))
        for shrineCount, val in enumerate(player["shrine_in_storage"]):
            place = shrineCount
            widthOfShrine = 24 * 5
            xspacing = 23 * 5
            yspacing = 28 * 5
            xLoc = (place % 3) * (xspacing + widthOfShrine)
            yLoc = (place // 3) * (yspacing + widthOfShrine)
            if val == 1:
                context.paste(shrine_image, (26 * 5 + xLoc, 25 * 5 + yLoc))

        byteData = BytesIO()
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="shrine_image.webp")
        return file

    def show_disc_tile(self, disc_tile_name: str):
        context = Image.new("RGBA", (260, 260), (255, 255, 255, 0))
        tile_image = Image.open("images/resources/components/discovery_tiles/discovery_" +
                                f"{disc_tile_name.replace(' ', '_').lower()}.png").convert("RGBA").resize((260, 260))
        context.paste(tile_image, (0, 0), mask=tile_image)
        byteData = BytesIO()
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="disc_tile_image.webp")
        return file

    def show_player_area(self, player_area):
        byteData = BytesIO()
        player_area.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="player_area.webp")
        return file

    def show_player_ship_area(self, player_area):
        player_area = player_area.crop((2250, 70, 3900+424+250, 470))
        byteData = BytesIO()
        player_area.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="player_area.webp")
        return file

    def show_player_ship(self, player_area, ship, factionName):
        player_area = player_area.crop((2250, 70, 3900+424+250, 470))
        if "intercept" in ship:
            player_area = player_area.crop((0, 0, 424, 400))
        if "cru" in ship:
                player_area = player_area.crop((550, 0, 550+424+100, 400))
        if "dread" in ship:
            player_area = player_area.crop((1100, 0, 1100+561,400))
        if "starbase" in ship or "orb" in ship:
            player_area = player_area.crop((1800, 0, 1800+424+100, 400))
        byteData = BytesIO()
        player_area.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="player_area.webp")
        return file

    def show_AI_stats(self):
        ai_ships = self.display_remaining_tiles().crop((40, 350, 480, 500))
        byteData = BytesIO()
        ai_ships.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="ai_ships.webp")
        return file

    @staticmethod
    def show_ref(ref_type):
        filepath = f"images/resources/components/reference_sheets/{ref_type}_referenceOrig.png"
        ref_image = Image.open(filepath)
        context = Image.new("RGBA", (1600, 2919), (255, 255, 255, 0))
        context.paste(ref_image, (0, 0), mask=ref_image)
        byteData = BytesIO()
        context.save(byteData, format="WEBP")
        byteData.seek(0)
        file = discord.File(byteData, filename="reference_image.webp")
        return file

    @staticmethod
    def show_tech_ref_image(tech_name, tech_type):
        context = Image.new("RGBA", (259, 257), (255, 255, 255, 0))
        fixed_name = tech_name.lower().replace(" ", "_")
        if tech_type == "any":
            filepath = f"images/resources/components/technology/rare/tech_{fixed_name}.png"
        else:
            filepath = f"images/resources/components/technology/{tech_type}/tech_{fixed_name}.png"
        tech_image = Image.open(filepath)
        context.paste(tech_image, (0, 0), mask=tech_image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tech_image.webp")

    @staticmethod
    def show_part_ref_image(part_name):
        context = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
        fixed_name = part_name.lower().replace(" ", "_")
        filepath = f"images/resources/components/upgrades/{fixed_name}.png"
        part_image = Image.open(filepath).convert("RGBA")
        context.paste(part_image, (0, 0), mask=part_image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="part_image.webp")

    @staticmethod
    def show_disc_tile_ref_image(tile_name):
        context = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
        fixed_name = "discovery_"+tile_name.lower().replace(" ", "_")
        filepath = f"images/resources/components/discovery_tiles/{fixed_name}.png"
        tile_image = Image.open(filepath).convert("RGBA")
        context.paste(tile_image, (0, 0), mask=tile_image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="WEBP")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tile_image.webp")
