import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
        elif full_name == "Eridian Empire":
            return "eridani"
        elif "terran" in full_name:
            return full_name.lower().replace(" ","_")

    def base_tile_image(self, sector):
        filepath = f"images/resources/hexes/{str(sector)}.png"
        if os.path.exists(filepath):
            tile_image = Image.open(filepath).convert("RGBA")
            tile_image = tile_image.resize((345, 299))
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
                count = 0
                for ship in tile["player_ships"]:
                    ship_image = Image.open(f"images/resources/components/basic_ships/{ship}.png").convert("RGBA")
                    ship_image = ship_image.resize((70, 70))
                    tile_image.paste(ship_image, (125 + count, 32 + count), mask=ship_image)
                    count += 20

            if "owner" in tile and tile["owner"] != 0:
                color = tile["owner"]
                inf_path = "images/resources/components/all_boards/influence_disc_"+color+".png"
                inf_image = Image.open(inf_path).convert("RGBA")
                inf_image = inf_image.resize((50, 50))
                tile_image.paste(inf_image, (148, 125), mask=inf_image)

            tile_image = tile_image.rotate(rotation)
            font = ImageFont.truetype("arial.ttf", size=45)
            text = str(position)
            text_position = (255, 132)
            text_color = (255, 255, 255)
            textDrawableImage = ImageDraw.Draw(tile_image)
            textDrawableImage.text(text_position, text, text_color, font=font)
            return tile_image

    def player_area(self, player):
        faction = self.get_short_faction_name(player["name"])
        filepath = "images/resources/components/factions/"+faction+"_board.png"
        context = Image.new("RGBA", (1200, 500), (255, 255, 255, 0))
        board_image = Image.open(filepath).convert("RGBA")
        board_image = board_image.resize((895, 500))
        context.paste(board_image, (0,0))
        x = 925
        y = 50
        font = ImageFont.truetype("arial.ttf", size=90)
        stroke_color=(0, 0, 0)
        stroke_width=2

        money_image = Image.open("images/resources/components/resourcesymbols/money.png").convert("RGBA")
        money_image = money_image.resize((100,100))
        science_image = Image.open("images/resources/components/resourcesymbols/science.png").convert("RGBA")
        science_image = science_image.resize((100, 100))
        material_image = Image.open("images/resources/components/resourcesymbols/material.png").convert("RGBA")
        material_image = material_image.resize((100, 100))

        context.paste(money_image, (x,y))
        text_color = (255, 255, 0)
        text_drawable_image = ImageDraw.Draw(context)
        text_drawable_image.text((x+120,y), str(player["money"]), text_color, font=font, stroke_width=stroke_width,
                                 stroke_fill=stroke_color)

        y = y+100
        context.paste(science_image, (x, y))
        text_color = (255, 192, 203)
        text_drawable_image = ImageDraw.Draw(context)
        text_drawable_image.text((x+120, y), str(player["science"]), text_color, font=font, stroke_width=stroke_width,
                                 stroke_fill=stroke_color)

        y = y + 100
        context.paste(material_image, (x, y))
        text_color = (101, 67, 33)
        text_drawable_image = ImageDraw.Draw(context)
        text_drawable_image.text((x + 120, y), str(player["materials"]), text_color, font=font,
                                 stroke_width=stroke_width,
                                 stroke_fill=stroke_color)
        return context

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