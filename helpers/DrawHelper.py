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


    def show_single_tile(self, tile_image):
        context = Image.new("RGBA", (345, 299), (255, 255, 255, 0))
        context.paste(tile_image, (0, 0), mask=tile_image)
        bytes = BytesIO()
        context.save(bytes, format="PNG")
        bytes.seek(0)
        file = discord.File(bytes, filename="tile_image.png")
        return file