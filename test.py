from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties

filepath = f"images/resources/components/factions/draco_board.png"
tile_image = Image.open(filepath).convert("RGBA")
#tile_image = tile_image.resize((345, 299))
tile_image = tile_image.crop((0, 0, 4096, 900))
#tile_image.show()
bytes = BytesIO()
tile_image.save(bytes, format="PNG")
bytes.seek(0)
file = bytes
