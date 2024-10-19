import math
import discord
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties
import json
import os
from discord.ui import View, Button

import time

from helpers.ImageCache import ImageCacheHelper

class DrawHelper:
    def __init__(self, gamestate):
        self.gamestate = gamestate

    def use_image(self, filename):  
        image_cache = ImageCacheHelper("images/resources")  # Get the singleton instance  
        image = image_cache.get_image(filename)  
        origFile = filename
        fineToGetOrig =  "Alone" in filename or"masks" in filename or"basic_ships" in filename or "factions" in filename or "reference" in filename or "technology" in filename or "upgrades" in filename
        if image:  
            if fineToGetOrig:
                return image
            else:
                return image.copy()  
        else:  
            filename = filename.split(f"/")[len(filename.split(f"/"))-1] 
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
        elif "Terran" in full_name:
            return full_name.lower().replace(" ","_")

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
        closedpath = f"images/resources/masks/closed_wh_mask.png"
        openpath = f"images/resources/masks/open_wh_mask.png"
        closed_mask = self.use_image(closedpath)
        open_mask = self.use_image(openpath)
        for wormhole in wormholes:
            wormholeCode = wormholeCode+str(wormhole)
        for i in range(6):
            tile_orientation_index = (i + 6 + int(rotation / 60)) % 6
            if tile_orientation_index in wormholes:
                tile_image.paste(open_mask, (154, 0), mask=open_mask)
            else:
                tile_image.paste(closed_mask, (154, 0), mask=closed_mask)
            tile_image = tile_image.rotate(60)
        return tile_image

    def draw_possible_oritentations(self, tileID, position, playerTiles, view:View, player):
        count = 1
        context = Image.new("RGBA", (345*3*3, 300*3*2+10), (255, 255, 255, 0))
        configs = Properties()
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
            rotation = x * 60
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
                adjTileWormholeNum = (index + 6 + x) % 6
                if rotationWorks: continue
                if adjTile in playerTiles and adjTileWormholeNum in tile["wormholes"]:
                    for index2, adjTile2 in enumerate(configs.get(adjTile)[0].split(",")):
                        tile_orientation_index2 = (index2 + 6 + int(int(self.gamestate["board"][adjTile]["orientation"]) / 60)) % 6
                        if adjTile2 == position and tile_orientation_index2 in self.gamestate["board"][adjTile]["wormholes"]:
                                rotationWorks = True
                                break
            if rotationWorks:
                context2 = self.base_tile_image_with_rotation_in_context(rotation, tileID, tile, count, configs, position)
                context.paste(context2, (345*3*((count-1)%3),910*(int((count-1)/3))),mask=context2)
                view.add_item(Button(label="Option #"+str(count),style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_placeTile_{position}_{tileID}_{rotation}"))
                count += 1
        bytes = BytesIO()
        if count < 5:
            context = context.crop((0,0,345*3*(count-1),300*3))
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="tile_image.png")
        return view,file




    def base_tile_image_with_rotation_in_context(self, rotation, tileID, tile, count, configs, position):
        context = Image.new("RGBA", (345*3, 300*3), (255, 255, 255, 0))
        image = self.base_tile_image_with_rotation(tileID,rotation,tile["wormholes"])
        context.paste(image,(345, 300),mask=image)
        coords = [(345, 0), (605, 150),(605, 450),(345, 600), (85, 450),(85, 150)]
        for index, adjTile in enumerate(configs.get(position)[0].split(",")):
            if adjTile in self.gamestate["board"]:
                adjTileImage = self.board_tile_image(adjTile)
                context.paste(adjTileImage,coords[index],mask=adjTileImage)
        font = ImageFont.truetype("images/resources/arial.ttf", size=80)
        ImageDraw.Draw(context).text((10, 10), f"Option #{count}", (255, 255, 255), font=font,
                        stroke_width=2, stroke_fill=(0, 0, 0))
        return context

    def board_tile_image_file(self,position):
        final_context = self.board_tile_image(position)
        bytes_io = BytesIO()
        final_context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tile_image.png")
    
    def availablePartsFile(self,available_parts):
        available_parts.discard("empty")
        context = Image.new("RGBA", (260*(len(available_parts)), 256), (255, 255, 255, 0))
        with open("data/parts.json", "r") as f:
                part_data = json.load(f)
        for x,part in enumerate(available_parts):
            part_details = part_data.get(part)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else part
            part_path = f"images/resources/components/upgrades/{partName}.png" 
            part_image = Image.open(part_path).resize((256,256))
            context.paste(part_image,(x*259, 0))
        
        bytes_io = BytesIO()
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="parts.png")
    
    def mergeLocationsFile(self,locations):
        amount = len(locations)
        sqrt_value = math.sqrt(amount)  
        result = int(math.ceil(sqrt_value))
        height = math.ceil(result * result / amount)
        if amount == 2:
            height = 1
        context = Image.new("RGBA", (360*result, 315*height), (255, 255, 255, 0))
        
        for count,tile in enumerate(locations):
            image = self.board_tile_image(tile)
            x = count % result
            y = int(count/result)
            context.paste(image,(x*360, y*315))
        bytes_io = BytesIO()
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tiles.png")

    def board_tile_image(self, position):
        sector = self.gamestate["board"][position]["sector"]
        filepath = f"images/resources/hexes/{sector}.png"


        if os.path.exists(filepath):
            tile_image = self.use_image(filepath)
            tile = self.gamestate["board"][position]
            rotation = int(tile["orientation"])

            if int(int(position) /100) == 2 and int(position) %2 == 1:
                hsMaskpath = f"images/resources/masks/hsmaskTrip.png"
                hsMask2 = Image.open(f"images/resources/masks/hsmaskTrip.png").convert("RGBA").resize((70, 70))
                tile_image.paste(hsMask2, (138, 115), mask=hsMask2)
            if "disctile" in tile and tile["disctile"] > 0:
                discPath = f"images/resources/components/discovery_tiles/discovery_2ptback.png"
                discTile = self.use_image(discPath)
                discTile = discTile.rotate(315,expand=True)
                tile_image.paste(discTile, (108, 89), mask=discTile)



            text_position = (268, 132)
            bannerPath = f"images/resources/masks/banner.png"
            banner = self.use_image(bannerPath)
            tile_image.paste(banner, (247, 126), mask=banner)

            font = ImageFont.truetype("images/resources/arial.ttf", size=30)
            text = str(position)

            text_color = (255, 255, 255)
            textDrawableImage = ImageDraw.Draw(tile_image)
            textDrawableImage.text(text_position, text, text_color, font=font)



            wormholeCode = ""
            closedpath = f"images/resources/masks/closed_wh_mask.png"
            openpath = f"images/resources/masks/open_wh_mask.png"
            greenpath = f"images/resources/masks/orange_open_wh_mask.png"
            blackpath = f"images/resources/masks/black_line.png"
            closed_mask = self.use_image(closedpath)
            open_mask = self.use_image(openpath)
            green = self.use_image(greenpath)
            black = self.use_image(blackpath)
            configs = Properties()
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
            if "wormholes" in tile:
                for wormhole in tile["wormholes"]:
                    wormholeCode = wormholeCode+str(wormhole)
                for i in range(6):
                    tile_orientation_index = (i + 6 + int(int(rotation) / 60)) % 6
                    if tile_orientation_index in tile["wormholes"]:
                        found = False
                        for x,adjTile in enumerate(configs.get(position)[0].split(",")):
                            if x==i and self.areTwoTilesAdjacent(position, adjTile, configs):
                                tile_image.paste(green, (152, 0), mask=green)
                                found = True
                                break
                        if not found:
                            tile_image.paste(open_mask, (152, 0), mask=open_mask)
                        
                    else:
                        tile_image.paste(closed_mask, (152, 0), mask=closed_mask)
                        tile_image.paste(black, (80, 0), mask=black)
                    tile_image = tile_image.rotate(60)

            if "warpDisc" in tile or "warpPoint" in tile:
                warppath = f"images/resources/all_boards/Warp_picture.png"
                warp_mask = self.use_image(warppath)
                tile_image.paste(warp_mask, (20, 140), mask=warp_mask)
            if "player_ships" in tile and len(tile["player_ships"]) > 0:
                counts = {}  # To track counts for each ship type
                countsShips = {}
                for ship in tile["player_ships"]:
                    ship_type = ship.split("-")[1]  # Extract ship type
                    size = 70
                    if ship not in countsShips:
                        countsShips[ship] = 0
                    countsShips[ship] += 10
                    if ship_type in ["gcds", "gcdsadv", "anc", "ancadv", "grd", "grdadv"]:
                        ship = ship_type.replace("adv","")
                        ship_type = "ai"
                        size = 110
                    if ship_type == "orb" or ship_type =="mon":
                        ship = ship_type
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
                        xCordToUse-=30
                        yCordToUse-=30
                    if "sb" in ship_type:
                        yCordToUse-=30

                    tile_image.paste(ship_image,
                                    (int(345 / 1024 * xCordToUse + counts[ship_type]-size/2),
                                    int(345 / 1024 * yCordToUse + counts[ship_type]-size/2)),
                                    mask=ship_image)
                    counts[ship_type] += 10
                    if ship_type == "ai":
                        counts[ship_type] += 20
                for key, value in countsShips.items():  
                    damage = 0
                    ship_type = "ai"
                    if "ai-" not in key:
                        ship_type=key.split("-")[1]

                    coords = tile[ship_type.replace("adv","")+"_snap"]
                    if "damage_tracker" in self.gamestate["board"][position]:
                        if key in self.gamestate["board"][position]["damage_tracker"]:
                            damage = self.gamestate["board"][position]["damage_tracker"][key]
                    if damage > 0:
                        for count in range(damage):
                            damage_image = self.use_image(f"images/resources/components/basic_ships/marker_damage.png")
                            tile_image.paste(damage_image,
                                    (int(345 / 1024 * coords[0] + value-size/2+count*10+15),
                                    int(345 / 1024 * coords[1] + value-size/2+35)),
                                    mask=damage_image)

            def paste_resourcecube(tile, tile_image, resource_type, color):
                if f"{resource_type}_pop" in tile and tile[f"{resource_type}_pop"] != 0 and tile[f"{resource_type}_pop"]:
                    popSize = tile[f"{resource_type}_pop"][0]
                    if len(tile[f"{resource_type}_pop"]) > 1:
                        popSize += tile[f"{resource_type}_pop"][1]
                    for x in range(popSize):
                        if (x+1) <= len(tile[f"{resource_type}_pop"]):
                            pop_path = f"images/resources/components/all_boards/popcube_{color}.png"
                            pop_image = self.use_image(pop_path)
                            if resource_type == "orbital":
                                coords = tile[f"orb_snap"]
                            else:
                                coords = tile[f"{resource_type}{x+1}_snap"]
                            tile_image.paste(pop_image, (int(345 / 1024 * coords[0] - 18), int(345 / 1024 * coords[1] - 18)), mask=pop_image)
                            if "money" in resource_type or "science" in resource_type or "material" in resource_type:
                                resource_type2 = resource_type.replace("adv","")+"_Alone"
                                pop_path = f"images/resources/components/resourcesymbols/{resource_type2}.png"
                                pop_image = self.use_image(pop_path).resize((40,40))
                                tile_image.paste(pop_image, (int(345 / 1024 * coords[0] - 20), int(345 / 1024 * coords[1] - 20)), mask=pop_image)

            if "owner" in tile and tile["owner"] != 0:
                color = tile["owner"]
                inf_path = f"images/resources/components/all_boards/influence_disc_{color}.png"
                inf_image = self.use_image(inf_path)
                tile_image.paste(inf_image, (153, 130), mask=inf_image)
                for resource in ["neutral", "neutraladv","money", "moneyadv", "science","scienceadv", "material","materialadv","orbital"]:
                    paste_resourcecube(tile, tile_image, resource, color)

            

            
            return tile_image
    
   
    def areTwoTilesAdjacent(self, tile1, tile2, configs):

        def is_adjacent(tile_a, tile_b):
            for index, adjTile in enumerate(configs.get(tile_a)[0].split(",")):
                if tile_a in self.gamestate["board"]:
                    tile_orientation_index = (index + 6 + int(int(self.gamestate["board"][tile_a]["orientation"]) / 60)) % 6
                    if adjTile == tile_b and "wormholes" in self.gamestate["board"][tile_a] and tile_orientation_index in self.gamestate["board"][tile_a]["wormholes"]:
                        return True
            return False

        return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)

    def display_techs(self):
        context = Image.new("RGBA", (2500, 470), (0,0,0,255))
        techsAvailable = self.gamestate["available_techs"]
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)

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
        x1=0
        x2=0
        x3=0
        x4=0
        largestX = 760
        ultimateX = 0
        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=70)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        text_drawable_image.text((120, 0), f"Available Techs", (255, 0, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        for tech_type in tech_groups:
            sorted_techs = sorted(tech_groups[tech_type], key=lambda x: x[2])  # Sort by cost
            size = 76
            last_tech = "bleh"
            for tech, tech_name, cost in sorted_techs:
                tech_details = tech_data.get(tech)
                techName = tech_details["name"].lower().replace(" ", "_") if tech_details else tech
                if tech_type == "military":
                    y=size*1
                    x1+=1
                    if techName == last_tech:
                        x1-=.7
                    ultimateX = int(x1*size)
                if tech_type == "grid":
                    y=size*2
                    x2+=1
                    if techName == last_tech:
                        x2-=.7
                    ultimateX = int(x2*size)
                elif tech_type == "nano":
                    y=size*3
                    x3+=1
                    if techName == last_tech:
                        x3-=.7
                    ultimateX = int(x3*size)
                elif tech_type == "any":
                    y=size*4
                    x4+=1
                    if techName == last_tech:
                        x4-=.7
                    ultimateX = int(x4*size)

               
                
                tech_path = f"images/resources/components/technology/{tech_type}/tech_{techName}.png"
                

                ultimateX += 100
                y +=50
                if not os.path.exists(tech_path):
                    tech_path = f"images/resources/components/technology/rare/tech_{techName}.png"
                tech_image = self.use_image(tech_path)
                tech_image = tech_image.resize((73,73))
                context.paste(tech_image, (ultimateX,y), mask=tech_image)
                largestX = max(largestX,ultimateX+73)
                last_tech = techName
        context = context.crop((0, 0,largestX,470))
        return context

    def display_remaining_tiles(self):
        context = Image.new("RGBA", (1300, 500), (0,0,0,255))


        filepath = f"images/resources/hexes/sector3backblank.png"

        tile_image = self.use_image(filepath).resize((172,150))
        context.paste(tile_image, (370,115), mask=tile_image)
        text_drawable_image = ImageDraw.Draw(context)
        font = ImageFont.truetype("images/resources/arial.ttf", size=70)
        stroke_color = (0, 0, 0)
        stroke_width = 2
        amount = len(self.gamestate["tile_deck_300"])

        if "tile_discard_deck_300"  in self.gamestate:
            amount += len(self.gamestate["tile_discard_deck_300"])

        text_drawable_image.text((565, 140), str(amount), (0, 255, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        text_drawable_image.text((0, 140), "Remaining           :", (0, 255, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        if "roundNum" in self.gamestate:
            round = self.gamestate["roundNum"]
        else:
            round = 1
        text_drawable_image.text((0, 0), "Round #"+str(round), (0, 255, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        
        text_drawable_image.text((0,270), "AI Stats:", (0, 255, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        x=0
        for ship_type in ["anc", "grd", "gcds"]:
            adv = ""
            if self.gamestate["advanced_ai"]:
                adv = "adv"
            if self.gamestate["wa_ai"]:
                adv = "wa"
            ship = "ai-"+ship_type+adv  
            filepathShip = f"images/resources/components/basic_ships/{ship}.png"
            ship_image = self.use_image(filepathShip)
            context.paste(ship_image, (50+x,350), mask=ship_image)
            x+=145

        text_drawable_image.text((630, 0), "Parts Reference:", (0, 255, 0), font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
        filepathRef = f"images/resources/components/reference_sheets/upgrade_reference1.png"
        ref_image = self.use_image(filepathRef)
        context.paste(ref_image, (660,80), mask=ref_image)
        filepathRef = f"images/resources/components/reference_sheets/upgrade_reference2.png"
        ref_image = self.use_image(filepathRef)
        context.paste(ref_image, (970,85), mask=ref_image)
        return context
    
    def display_cube_track_reference(self, player):
        context = Image.new("RGBA", (1690, 125), (0,0,0,255))

        spaces = [28,24,21,18,15,12,10,8,6,4,3,2,0]
        pop_path = f"images/resources/components/all_boards/popcube_{player['color']}.png"
        
        font = ImageFont.truetype("images/resources/arial.ttf", size=50)
        stroke_color = (0, 0, 0)

        if player['color'] == "purple" or player['color'] == "blue":
            color = (255, 255, 255)
        else:
            color = (0, 0, 0)
        stroke_width = 1
        pop_image = self.use_image(pop_path).resize((220,75))
        context.paste(pop_image, (0,25), mask=pop_image)
        text_drawable_image = ImageDraw.Draw(context)
        text_drawable_image.text((18,35), "Income:", color, font=font,
                            stroke_width=stroke_width, stroke_fill=stroke_color)
        
        
            
         # Resource details: [(image_path, text_color, player_key, amount_key)]
        resources = [
            ("images/resources/components/resourcesymbols/money.png", "images/resources/components/all_boards/popcube_orange.png","money_pop_cubes", (0, 0)),
            ("images/resources/components/resourcesymbols/science.png", "images/resources/components/all_boards/popcube_pink.png","science_pop_cubes",(0, 95)),
            ("images/resources/components/resourcesymbols/material.png","images/resources/components/all_boards/popcube_brown.png", "material_pop_cubes",(35, 95))
        ]

        def draw_resourceCube(context, pop_path, amount_key):
            population_track = player["population_track"]  
            pop_image = self.use_image(pop_path).resize((95,95))
            amount_index = player[amount_key] - 1  
            if 0 <= amount_index < len(population_track):  
                population_value = population_track[amount_index]  
            else:  
                population_value = 2   
            ind = spaces.index(population_value) +1
            context.paste(pop_image, (1390 - ind*90,15))

        def draw_resource(context, img_path, amount_key, position):
            image = self.use_image(img_path).resize((30,30))
            population_track = player["population_track"]  
            amount_index = player[amount_key] - 1  
            if 0 <= amount_index < len(population_track):  
                population_value = population_track[amount_index]  
            else:  
                population_value = 2   
            ind = spaces.index(population_value) +1
            context.paste(image, (position[0]+1405 - ind*90,position[1]))

        for img_path, color_path, amount_key, position in resources:
            draw_resourceCube(context, color_path, amount_key)
        for img_path, color_path, amount_key, position in resources:
            draw_resource(context, img_path, amount_key, position)

        pop_image = self.use_image(pop_path).resize((75,75))
        for count,num in enumerate(spaces):
            x=  1310 - count*90
            context.paste(pop_image, (x,25), mask=pop_image)
            mod = 0
            if num > 9:
                mod = 12
            text_drawable_image.text((x+20-mod,35), str(num), color, font=font,
                            stroke_width=stroke_width, stroke_fill=stroke_color)
        return context

    def player_area(self, player):
        faction = self.get_short_faction_name(player["name"])
        filepath = "images/resources/components/factions/"+str(faction)+"_board.png"
        context = Image.new("RGBA", (1440, 625), (0,0,0,255))
        board_image = self.use_image(filepath)
        context.paste(board_image, (0,0))
        inf_path = "images/resources/components/all_boards/influence_disc_"+player["color"]+".png"
        inf_image = self.use_image(inf_path)

        for x in range(player["influence_discs"]):
            context.paste(inf_image, (764-(int(x*38.5)), 450), mask=inf_image)

        for x,action in enumerate(["explore","research","upgrade","build","move","influence"]):
            if action+"_action_counters" in player:
                num = player[action+"_action_counters"]
                if num > 0:
                    context.paste(inf_image, (12+(int(x*47)), 422), mask=inf_image)
                if num > 1:
                    font = ImageFont.truetype("images/resources/arial.ttf", size=25)
                    stroke_color = (0, 0, 0)
                    color = (255, 255, 255)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context)
                    text_drawable_image.text((17+(int(x*47)), 426), "x"+str(num), color, font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)


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
                context.paste(tech_image, (299 + (counter * 71), start_y), mask=tech_image)

        process_tech(player["nano_tech"], "nano", 360)
        process_tech(player["grid_tech"], "grid", 285)
        process_tech(player["military_tech"], "military", 203)

        # Last coord is for muon source exclusively
        interceptCoord = [ (74, 39),(16, 86), (74, 97), (132, 86), (148, 39)]
        cruiserCoord = [(221, 63), (279, 39),(337, 63),(221, 121), (279, 97),(337, 121), (353, 19)]
        dreadCoord = [(435, 64), (493, 40),(551, 40),(609, 64),(435, 122), (493, 98),(551, 98),(609, 122), (628, 20)]
        sbCoord = [(697, 39),(813, 39),(697, 97),(755, 66), (814, 97),(815, 0)]

        if player["name"]=="Planta":
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
                    part_image = part_image.resize((40,40))
                context.paste(part_image, coords[counter], mask=part_image)

        process_parts(player["interceptor_parts"], interceptCoord)
        process_parts(player["cruiser_parts"], cruiserCoord)
        process_parts(player["dread_parts"], dreadCoord)
        process_parts(player["starbase_parts"], sbCoord)

        sizeR = 58
        reputation_path = f"images/resources/components/all_boards/reputation.png"
        reputation_image = self.use_image(reputation_path)
        mod = 0
        scaler = 86
        if len(player["reputation_track"]) > 4:
            scaler = 67
            mod = 3
        for x,reputation in enumerate(player["reputation_track"]):
            if isinstance(reputation, int):
                if "gameEnded" in self.gamestate:
                    pointsPath = "images/resources/components/all_boards/points.png"
                    points = self.use_image(pointsPath).resize(((58,58)))
                    context.paste(points, (825,172+x*scaler-mod), mask=points)
                    font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                    stroke_color = (0, 0, 0)
                    color = (0, 0, 0)
                    stroke_width = 2
                    text_drawable_image = ImageDraw.Draw(context)
                    text_drawable_image.text((825+13,172+x*scaler-mod), str(reputation), color, font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
                else:
                    context.paste(reputation_image, (825,172+x*scaler-mod), mask=reputation_image)
            if not isinstance(reputation, int) and "-" in reputation:
                faction = reputation.split("-")[1]
                color =  reputation.split("-")[2]
                pop_path = f"images/resources/components/all_boards/popcube_{color}.png"
                pop_image = self.use_image(pop_path)
                amb_tile_path = f"images/resources/components/factions/{faction}_ambassador.png"
                amb_tile_image = self.use_image(amb_tile_path)
                context.paste(amb_tile_image, (825,172+x*scaler-mod), mask=amb_tile_image)
                context.paste(pop_image, (825+20,172+x*scaler+25-mod), mask=pop_image)

        x = 925
        y = 0
        font = ImageFont.truetype("images/resources/arial.ttf", size=90)
        stroke_color = (0, 0, 0)
        stroke_width = 2

        if "passed" in player and player["passed"] == True:
            text_image = Image.new('RGBA', (500,500), (0, 0, 0, 0))
            text_drawable = ImageDraw.Draw(text_image)
            text_drawable.text((0, 50), "Passed", fill=(255, 0, 0), font=font, stroke_width=stroke_width, stroke_fill=stroke_color)
            text_image = text_image.rotate(45, expand=True)
            context.paste(text_image, (0, 0), text_image)

        

        # Resource details: [(image_path, text_color, player_key, amount_key)]
        resources = [
            ("images/resources/components/resourcesymbols/money.png", (255, 255, 0), "money", "money_pop_cubes"),
            ("images/resources/components/resourcesymbols/science.png", (255, 192, 203), "science", "science_pop_cubes"),
            ("images/resources/components/resourcesymbols/material.png", (101, 67, 33), "materials", "material_pop_cubes")
        ]

        def draw_resource(context, img_path, color, player_key, amount_key, position):
            image = self.use_image(img_path)
            context.paste(image, position)
            text_drawable_image = ImageDraw.Draw(context)
            text_drawable_image.text((position[0] + 120, position[1]), f"{player[player_key]}", color, font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
            
        newY = y 
        newX = x+240
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        
        listOfAncient = player["ancient_parts"]
        if "discoveryTileBonusPointTiles" in player:
            listOfAncient = listOfAncient + player["discoveryTileBonusPointTiles"]
        for part in listOfAncient:
            discName = discTile_data[part]["name"]
            part_path = f"images/resources/components/discovery_tiles/discovery_{discName.replace(' ','_').lower()}.png"
            part_image = self.use_image(part_path)
            context.paste(part_image, (newX, newY), mask=part_image)
            newY+=85
        for img_path, text_color, player_key, amount_key in resources:
            draw_resource(context, img_path, text_color, player_key, amount_key, (x, y))
            y += 100
        colonyPath = "images/resources/components/all_boards/colony_ship.png"
        colonyShip = self.use_image(colonyPath)

        for i in range(player["colony_ships"]):
            context.paste(colonyShip, (x+i*50,y+10),colonyShip)


        publicPoints = self.get_public_points(player)
        pointsPath = "images/resources/components/all_boards/points.png"
        points = self.use_image(pointsPath)
        context.paste(points, (x+250,y+10),points)
        font = ImageFont.truetype("images/resources/arial.ttf", size=50)
        stroke_color = (0, 0, 0)
        color = (0, 0, 0)
        stroke_width = 2
        text_drawable_image = ImageDraw.Draw(context)
        letX = x+250+25
        if publicPoints > 9:
            letX = x+250+12
        text_drawable_image.text((letX,y+21), str(publicPoints), color, font=font,
                        stroke_width=stroke_width, stroke_fill=stroke_color)
       
        y += 90
        ships = ["int","cru","drd","sb"]
        ultimateC = 0
        for counter,ship in enumerate(ships):
            filepath = f"images/resources/components/basic_ships/{player['color']}-{ship}.png"
            ship_image = self.use_image(filepath)
            for shipCounter in range(player["ship_stock"][counter]):
                context.paste(ship_image, (x+ultimateC*10+counter*70,y),ship_image)
                ultimateC +=1

        discTile = Image.open(f"images/resources/components/discovery_tiles/discovery_2ptback.png").convert("RGBA").resize((40, 40))
        discTile = discTile.rotate(315,expand=True)
        if "disc_tiles_for_points" in player:
            for discT in range(player["disc_tiles_for_points"]):
                context.paste(discTile, (x+discT*25,y+50), mask=discTile)

        context2 = self.display_cube_track_reference(player)
        context.paste(context2,(0,500))
        return context

    def get_public_points(self, player):
        points = 0
        tile_map = self.gamestate["board"]
        color = player["color"]
        tiles = []
        for tile in tile_map:
            if "owner" in tile_map[tile] and tile_map[tile]["owner"] == color:
                points += tile_map[tile]["vp"]
                if "warpPoint" in tile_map[tile]:
                    points += tile_map[tile]["warpPoint"]
                if "warpDisc" in tile_map[tile]:
                    points += tile_map[tile]["warpDisc"]
                if "discoveryTileBonusPointTiles" in player and "art" in player["discoveryTileBonusPointTiles"] and tile_map[tile]["artifact"] == 1:
                    points += 1
                if "player_ships" in tile_map[tile]:
                    for ship in tile_map[tile]["player_ships"]:
                        if "mon" in ship:
                            points += 3
                if player["name"] == "Planta":
                    points +=1
            if player["name"] == "Descendants of Draco" and "player_ships" in tile_map[tile]:
                for ship in tile_map[tile]["player_ships"]:
                    if "anc" in ship:
                        points += 1
        techTypes =["military_tech","grid_tech","nano_tech"]
        for type in techTypes:
            if type in player and len(player[type]) > 4:
                if len(player[type]) == 7:
                    points += 5
                else:
                    points += len(player[type])-3
        if "disc_tiles_for_points" in player:
            points += player["disc_tiles_for_points"]*2
        reputationPoints = 0
        for reputation in player["reputation_track"]:
            if isinstance(reputation, int):
                if "gameEnded" in self.gamestate:
                    points += reputation
                    reputationPoints +=reputation
            if not isinstance(reputation, int) and "-" in reputation:
                points += 1
        if "discoveryTileBonusPointTiles" in player and "rep" in player["discoveryTileBonusPointTiles"]:
            points += int(reputationPoints/3)
        if "traitor" in player and player["traitor"] == True:
            points -= 2
        return points
    
    #effectively discontinued in favor of show_map and show_stats
    def show_game(self):
        start_time = time.perf_counter() 
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

        def create_player_area():
            pCount = len(self.gamestate["players"])
            player_area_length = 1200 if pCount > 3 else 600
            width = 4420 if (pCount != 2 and pCount != 4) else 2990
            context2 = Image.new("RGBA", (width, player_area_length), (255, 255, 255, 0))
            x, y, count = 100, 100, 0
            for player in self.gamestate["players"]:
                player_image = self.player_area(self.gamestate["players"][player])
                context2.paste(player_image, (x, y), mask=player_image)
                count += 1
                if count % 2 == 0 and pCount == 4:
                    x = 100  # Reset x back to the starting position
                    y += 600
                elif count % 3 == 0 and pCount != 4:
                    x = 100  # Reset x back to the starting position
                    y += 600
                else:
                    x += 1440
            return context2


        
        context = Image.new("RGBA", (4160, 5100), (255, 255, 255, 0))
        min_x, min_y, max_x, max_y = paste_tiles(context, self.gamestate["board"])

        board_width = max_x - min_x
        board_height = max_y - min_y
        cropped_context = context.crop((0, min_y, 4160, max_y))
        context2 = create_player_area()
        context3 = self.display_techs()
        context4 = self.display_remaining_tiles()
        context5 = self.display_cube_track_reference()
        end_time = time.perf_counter()  
        elapsed_time = end_time - start_time  
        print(f"Total elapsed time for generating all contexts: {elapsed_time:.2f} seconds")
        start_time = time.perf_counter() 
        final_context = Image.new("RGBA", (4160, board_height + context2.size[1]+context3.size[1]), (255, 255, 255, 0))
        final_context.paste(cropped_context, (0, 0))
        final_context.paste(context2, (0, board_height))
        final_context.paste(context3, (0, board_height+context2.size[1]))
        final_context.paste(context5, (50, board_height+context2.size[1]-20))
        final_context.paste(context4, (1500, board_height+context2.size[1]))
        
        final_context = final_context.resize((int(final_context.width/1.5),int(final_context.height/1.5)))
        bytes_io = BytesIO()
        final_context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        end_time = time.perf_counter()  
        elapsed_time = end_time - start_time  
        print(f"Total elapsed time for pasting all together: {elapsed_time:.2f} seconds")
        return discord.File(bytes_io, filename="map_image.png")
    
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
        context = Image.new("RGBA", (4160, 5100), (0,0,0,255))
        min_x, min_y, max_x, max_y = paste_tiles(context, self.gamestate["board"])
        cropped_context = context.crop((min_x, min_y, max_x, max_y))
        cropped_context=cropped_context.resize([int((max_x-min_x)/2),int((max_y-min_y)/2)])
        bytes_io = BytesIO()
        cropped_context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="map_image.png")
    
    def get_file(self, imageName:str):
        bytes_io = BytesIO()
        image = self.use_image(imageName)
        image.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="image.png")
    
    def append_images(self, images):

        image1 = images[0]
        context = Image.new("RGBA", ((image1.size[0]+10) * len(images), image1.size[1]), (255, 255, 255, 0))
        for x,image in enumerate(images):
            context.paste(image, (x*(image1.size[0]+10),0),mask=image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="image.png")


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

                    if "traitor" in self.gamestate["players"][player] and self.gamestate["players"][player]["traitor"] == True:
                        username = username + " (TRAITOR)"
                    text_drawable_image.text((x,y), username, color, font=font,
                                    stroke_width=stroke_width, stroke_fill=stroke_color)
                context2.paste(player_image, (x, y+50), mask=player_image)
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
        context3 = self.display_techs()
        context4 = self.display_remaining_tiles()
        #context5 = self.display_cube_track_reference()
        pCount = len(self.gamestate["players"])
        width = 4150 if (pCount != 2 and pCount != 4) else 2800
        width = max(context2.size[0],context3.size[0]+context4.size[0]+150)
        final_context = Image.new("RGBA", (width, context2.size[1]+max(context3.size[1],context4.size[1])), (0, 0, 0, 255))
        final_context.paste(context2, (0, 0))
        final_context.paste(context3, (0, context2.size[1]))
        #final_context.paste(context5, (50, context2.size[1]-20))
        final_context.paste(context4, (context3.size[0]+150, context2.size[1]))
        
        bytes_io = BytesIO()
        final_context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="stats_image.png")

    def show_available_techs(self):
        context = self.display_techs()
        bytes_io = BytesIO()
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)

        return discord.File(bytes_io, filename="techs_image.png")

    def show_single_tile(self, tile_image):
        context = Image.new("RGBA", (345, 299), (255, 255, 255, 0))
        context.paste(tile_image, (0,0), mask=tile_image)
        bytes = BytesIO()
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="tile_image.png")
        return file

    def show_disc_tile(self, disc_tile_name:str):
        context = Image.new("RGBA", (260, 260), (255, 255, 255, 0))
        tile_image = Image.open(f"images/resources/components/discovery_tiles/discovery_{disc_tile_name.replace(' ','_').lower()}.png").convert("RGBA").resize((260, 260))
        context.paste(tile_image, (0,0), mask=tile_image)
        bytes = BytesIO()
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="disc_tile_image.png")
        return file

    def show_player_area(self, player_area):
        bytes = BytesIO()
        player_area.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="player_area.png")
        return file

    def show_player_ship_area(self, player_area):
        player_area = player_area.crop((0,0,895, 196))
        bytes = BytesIO()
        player_area.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="player_area.png")
        return file

    def show_player_ship(self, player_area, ship):
        player_area = player_area.crop((0,0,895, 196))
        if "intercept" in ship:
            player_area = player_area.crop((16,0,200, 170))
        if "cru" in ship:
            player_area = player_area.crop((221,0,405, 196))
        if "dread" in ship:
            player_area = player_area.crop((435,0,680, 196))
        if "starbase" in ship:
            player_area = player_area.crop((696,0,875, 160))
        bytes = BytesIO()
        player_area.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="player_area.png")
        return file
    
    def show_AI_stats(self):
        ai_ships = self.display_remaining_tiles().crop((50,350,500, 500))
        bytes = BytesIO()
        ai_ships.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="ai_ships.png")
        return file

    @staticmethod
    def show_ref(ref_type):
        filepath = f"images/resources/components/reference_sheets/{ref_type}_referenceOrig.png"
        ref_image = Image.open(filepath)
        context = Image.new("RGBA", (1600, 2919), (255, 255, 255, 0))
        context.paste(ref_image, (0,0), mask=ref_image)
        bytes = BytesIO()
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="reference_image.png")
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
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="tech_image.png")

    @staticmethod
    def show_part_ref_image(part_name):
        context = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
        fixed_name = part_name.lower().replace(" ", "_")
        filepath = f"images/resources/components/upgrades/{fixed_name}.png"
        part_image = Image.open(filepath)
        context.paste(part_image, (0, 0), mask=part_image)
        bytes_io = BytesIO()
        context.save(bytes_io, format="PNG")
        bytes_io.seek(0)
        return discord.File(bytes_io, filename="part_image.png")
