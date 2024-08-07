import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties
import json
import os

class DrawHelper:
    def __init__(self, gamestate):
        self.gamestate = gamestate

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
            tile_image = Image.open(filepath).convert("RGBA")
            tile_image = tile_image.resize((345, 299))
            return tile_image
    def base_tile_image_with_rotation(self, sector, rotation, wormholes):
        wormholeCode = ""
        filepath = f"images/resources/hexes/{str(sector)}.png"
        if os.path.exists(filepath):
            tile_image = Image.open(filepath).convert("RGBA")
            tile_image = tile_image.resize((345, 299))
        closed_mask = Image.open(f"images/resources/masks/closed_wh_mask.png").convert("RGBA").resize((42, 22))
        open_mask = Image.open(f"images/resources/masks/open_wh_mask.png").convert("RGBA").resize((42, 22))
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

    def board_tile_image(self, position):
        sector = self.gamestate["board"][position]["sector"]
        filepath = f"images/resources/hexes/{sector}.png"


        if os.path.exists(filepath):
            tile_image = Image.open(filepath).convert("RGBA")
            tile_image = tile_image.resize((345, 299))
            tile = self.gamestate["board"][position]
            rotation = tile["orientation"]

            if "player_ships" in tile and len(tile["player_ships"]) > 0:  
                counts = {}  # To track counts for each ship type  
                for ship in tile["player_ships"]:  
                    ship_type = ship.split("-")[1]  # Extract ship type
                    ship_image = Image.open(f"images/resources/components/basic_ships/{ship}.png").convert("RGBA").resize((70, 70))  
                    coords = tile[f"{ship_type}_snap"]  
                     
                    if ship_type not in counts:  
                        counts[ship_type] = 0  
                    
                    tile_image.paste(ship_image,   
                                    (int(345 / 1024 * coords[0] + counts[ship_type]-35),   
                                    int(345 / 1024 * coords[1] + counts[ship_type]-35)),   
                                    mask=ship_image)  
                    
                    counts[ship_type] += 10 

            def paste_resourcecube(tile, tile_image, resource_type, color):  
                if f"{resource_type}_pop" in tile and tile[f"{resource_type}_pop"] != 0 and tile[f"{resource_type}_pop"]:  
                    for x in range(tile[f"{resource_type}_pop"][0]):  
                        pop_path = f"images/resources/components/all_boards/popcube_{color}.png"  
                        pop_image = Image.open(pop_path).convert("RGBA").resize((30, 30))  
                        coords = tile[f"{resource_type}{x+1}_snap"]  
                        tile_image.paste(pop_image, (int(345 / 1024 * coords[0] - 15), int(345 / 1024 * coords[1] - 15)), mask=pop_image)  

            if "owner" in tile and tile["owner"] != 0:  
                color = tile["owner"]  
                inf_path = f"images/resources/components/all_boards/influence_disc_{color}.png"  
                inf_image = Image.open(inf_path).convert("RGBA").resize((50, 50))  
                tile_image.paste(inf_image, (148, 125), mask=inf_image)    
                for resource in ["money", "moneyadv", "science","scienceadv", "material","materialadv"]:  
                    paste_resourcecube(tile, tile_image, resource, color)  

            wormholeCode = ""
            closed_mask = Image.open(f"images/resources/masks/closed_wh_mask.png").convert("RGBA").resize((42, 22))
            open_mask = Image.open(f"images/resources/masks/open_wh_mask.png").convert("RGBA").resize((42, 22))
            if "wormholes" in tile:
                for wormhole in tile["wormholes"]:
                    wormholeCode = wormholeCode+str(wormhole)
                for i in range(6):
                    tile_orientation_index = (i + 6 + int(rotation / 60)) % 6
                    if tile_orientation_index in tile["wormholes"]:
                        tile_image.paste(open_mask, (154, 0), mask=open_mask)
                    else:
                        tile_image.paste(closed_mask, (154, 0), mask=closed_mask)
                    tile_image = tile_image.rotate(60)
                  #345, 299

            if "disctile" in tile and tile["disctile"] > 0:
                discTile = Image.open(f"images/resources/components/discovery_tiles/discovery_2ptback.png").convert("RGBA").resize((90, 90))
                discTile = discTile.rotate(315,expand=True)
                tile_image.paste(discTile, (112, 88), mask=discTile)



            text_position = (268, 132)
            banner = Image.open(f"images/resources/masks/banner.png").convert("RGBA").resize((98, 48))
            tile_image.paste(banner, (247, 126), mask=banner)





            font = ImageFont.truetype("arial.ttf", size=30)
            text = str(position)
            
            text_color = (255, 255, 255)
            textDrawableImage = ImageDraw.Draw(tile_image)
            textDrawableImage.text(text_position, text, text_color, font=font)
            return tile_image

    def player_area(self, player):
        faction = self.get_short_faction_name(player["name"])
        filepath = "images/resources/components/factions/"+str(faction)+"_board.png"
        context = Image.new("RGBA", (1300, 500), (255, 255, 255, 0))
        board_image = Image.open(filepath).convert("RGBA")
        board_image = board_image.resize((895, 500))
        context.paste(board_image, (0,0))
        inf_path = "images/resources/components/all_boards/influence_disc_"+player["color"]+".png"
        inf_image = Image.open(inf_path).convert("RGBA")
        inf_image = inf_image.resize((40, 40))

        for x in range(player["influence_discs"]):
            context.paste(inf_image, (764-(int(x*38.5)), 450), mask=inf_image)

        for x,action in enumerate(["explore","research","upgrade","build","move","influence"]):  
            if action+"_action_counters" in player:
                num = player[action+"_action_counters"]
                if num > 0:
                    context.paste(inf_image, (12+(int(x*47)), 422), mask=inf_image)
                if num > 1:
                    font = ImageFont.truetype("arial.ttf", size=25)  
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
                tech_image = Image.open(tech_path).convert("RGBA").resize((68, 68))  
                context.paste(tech_image, (299 + (counter * 71), start_y), mask=tech_image)  

        process_tech(player["nano_tech"], "nano", 360)  
        process_tech(player["grid_tech"], "grid", 285)  
        process_tech(player["military_tech"], "military", 203)  


        interceptCoord = [ (74, 39),(16, 86), (74, 97), (132, 86)] 
        cruiserCoord = [(221, 63), (279, 39),(337, 63),(221, 121), (279, 97),(337, 121)]  
        dreadCoord = [(435, 64), (493, 40),(551, 40),(609, 64),(435, 122), (493, 98),(551, 98),(609, 122)]   
        sbCoord = [(697, 39),(813, 39),(697, 97),(755, 66), (814, 97)]  

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
                part_image = Image.open(part_path).convert("RGBA").resize((58, 58))  
                context.paste(part_image, coords[counter], mask=part_image)  

        process_parts(player["interceptor_parts"], interceptCoord)  
        process_parts(player["cruiser_parts"], cruiserCoord)  
        process_parts(player["dread_parts"], dreadCoord)  
        process_parts(player["starbase_parts"], sbCoord)  
            


        x = 925  
        y = 50  
        font = ImageFont.truetype("arial.ttf", size=90)  
        stroke_color = (0, 0, 0)  
        stroke_width = 2  

        # Resource details: [(image_path, text_color, player_key, amount_key)]  
        resources = [  
            ("images/resources/components/resourcesymbols/money.png", (255, 255, 0), "money", "money_pop_cubes"),  
            ("images/resources/components/resourcesymbols/science.png", (255, 192, 203), "science", "science_pop_cubes"),  
            ("images/resources/components/resourcesymbols/material.png", (101, 67, 33), "materials", "material_pop_cubes")  
        ]  

        def draw_resource(context, img_path, color, player_key, amount_key, position):  
            image = Image.open(img_path).convert("RGBA").resize((100, 100))  
            context.paste(image, position)  
            amountIncrease = player["population_track"][player[amount_key]-1] - (player["influence_track"][player["influence_discs"]] if player_key == "money" else 0)
            if amountIncrease > -1:
                amountIncrease = "+"+str(amountIncrease)
            else:
                amountIncrease = str(amountIncrease)  
            text_drawable_image = ImageDraw.Draw(context)  
            text_drawable_image.text((position[0] + 120, position[1]), f"{player[player_key]}({amountIncrease})", color, font=font,  
                                    stroke_width=stroke_width, stroke_fill=stroke_color)  

        for img_path, text_color, player_key, amount_key in resources:  
            draw_resource(context, img_path, text_color, player_key, amount_key, (x, y))  
            y += 100 
        
        return context


    def show_tile_in_context(self, tile_map, tile, position, rotation, context):
        for tile in tile_map:  
            tile_image = self.board_tile_image(tile)  
            x, y = map(int, configs.get(tile)[0].split(","))  
            context.paste(tile_image, (x, y), mask=tile_image)

    def show_game(self):  
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
            player_area_length = 1200 if len(self.gamestate["players"]) > 3 else 600  
            context2 = Image.new("RGBA", (4160, player_area_length), (255, 255, 255, 0))  
            x, y, count = 100, 100, 0  
            for player in self.gamestate["players"]:  
                player_image = self.player_area(self.gamestate["players"][player])  
                context2.paste(player_image, (x, y), mask=player_image)  
                count += 1  
                if count % 3 == 0:  
                    x = 100  # Reset x back to the starting position  
                    y += 600  
                else:  
                    x += 1350  
            return context2  

        # Create context for the main board  
        context = Image.new("RGBA", (4160, 5100), (255, 255, 255, 0))  
        min_x, min_y, max_x, max_y = paste_tiles(context, self.gamestate["board"]) 

        board_width = max_x - min_x  
        board_height = max_y - min_y  
        cropped_context = context.crop((0, min_y, 4160, max_y)) 
        # Create context for players  
        context2 = create_player_area()  

        # Combine both contexts  
        final_context = Image.new("RGBA", (4160, board_height + context2.size[1]), (255, 255, 255, 0))  
        final_context.paste(cropped_context, (0, 0))  
        final_context.paste(context2, (0, board_height))  

        bytes_io = BytesIO()  
        final_context.save(bytes_io, format="PNG")  
        bytes_io.seek(0)  

        return discord.File(bytes_io, filename="map_image.png") 

    def show_single_tile(self, tile_image):
        context = Image.new("RGBA", (345, 299), (255, 255, 255, 0))
        context.paste(tile_image, (0,0), mask=tile_image)
        bytes = BytesIO()
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="tile_image.png")
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