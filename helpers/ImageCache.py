from PIL import Image
import os


class ImageCacheHelper:
    _instance = None

    def __new__(cls, base_directory):
        if cls._instance is None:
            cls._instance = super(ImageCacheHelper, cls).__new__(cls)
            cls._instance.base_directory = base_directory
            cls._instance.cache = {}
            cls._instance.load_images()
        return cls._instance

    def load_images(self):
        for root, dirs, files in os.walk(self.base_directory):
            for filename in files:
                if filename.endswith(('.png')):
                    if "mask" in filename and "_" not in filename:
                        continue
                    image_path = os.path.join(root, filename)
                    size = self.get_image_size(root, filename)
                    if "wh_mask" in filename:
                        self.cache[filename] = Image.open(image_path).convert("RGBA").resize(size).rotate(180)
                    else:
                        imageTemp = Image.open(image_path).convert("RGBA")
                        if imageTemp.size != size:
                            imageTemp = imageTemp.resize(size)
                        if "fancy" in root and "drd" in filename:
                            imageTemp = imageTemp.rotate(-30)
                        self.cache[filename] = imageTemp

    def get_image_size(self, folder, filename):
        mult = 1024/345
        if "hexes" in folder.lower():
            if "hyper" in filename.lower():
                return (1125, 900)
            return (int(345 * mult), int(300 * mult))
        elif "upgrade_reference1" in filename.lower() or "upgrade_reference2" in filename.lower():
            return (310, 300)
        elif "masks" in folder.lower():
            if "banner" in filename.lower():
                return (int(98 * mult), int(48 * mult))
            elif "hsMask" in filename.lower():
                return (int(70 * mult), int(70 * mult))
            elif "line" in filename.lower():
                # 178
                return (int(182 * mult), int(5 * mult))
            else:
                return (int(42 * mult), int(22 * mult))
        elif "factions" in folder.lower():
            if "ambassador" in filename.lower():
                return (58, 58)
            elif "shrine_board" in filename.lower():
                return (187*2, 171*2)
            elif "shrine" in filename.lower():
                return (24*2, 24*2)
            elif "reference" in filename.lower():
                return Image.open(os.path.join(folder, filename)).convert("RGBA").size
            else:
                return (895, 500)
        elif "minor_species" in folder.lower():
            return (58, 58)
        elif "energy" in folder.lower():
            return (54, 116)
        elif "all_boards" in folder.lower():
            if "popcube" in filename.lower():
                return (int(35 * mult), int(35 * mult))
            elif "influence_disc" in filename.lower():
                return (int(40 * mult), int(40 * mult))
            elif "reputation" in filename.lower():
                return (110, 110)
            elif "colony_ship" in filename.lower():
                return (100, 100)
            elif "points" in filename.lower():
                return (80, 80)
            elif "yellow_square" in filename.lower():
                return (65, 65)
            elif "warp_picture" in filename.lower():
                return (int(132 * mult), int(102 * mult))
            else:
                return (80, 80)
        elif "basic_ships" in folder.lower() or "fancy_ships" in folder.lower():
            if any(substring in filename.lower().replace("fancy", "")
                   for substring in ["gcds", "gcdsadv", "anc", "ancadv", "grd", "grdadv","orb"]):
                if "ai" in filename.lower():
                    return (int(160), int(160))
                else:
                    return (int(110 * mult), int(110 * mult))
            else:
                if "mon" in filename.lower():
                    return (int(90 * mult), int(90 * mult))
                if "damage" in filename.lower():
                    return (int(15 * mult), int(15 * mult))
                else:
                    if "basic_ships" in folder.lower():
                        if "cru" in filename.lower() or "sb" in filename.lower():
                            return (int(90 * mult), int(90 * mult))
                        else:
                            if "drd" in filename.lower():
                                return (int(90 * mult), int(90 * mult))
                            else:
                                return (int(70 * mult), int(70 * mult))
                    else:
                        if "cru" in filename.lower() or "sb" in filename.lower():
                            return (int(70 * mult), int(70 * mult))
                        else:
                            if "drd" in filename.lower():
                                return (int(100 * mult), int(100 * mult))
                            else:
                                return (int(40 * mult), int(40 * mult))
        elif "discovery_tiles" in folder.lower():
            return (int(80 * mult), int(80 * mult))
        elif "upgrades" in folder.lower():
            return (140, 140)
        elif "resourcesymbol" in folder.lower():
            if "alone" in filename.lower():
                return (int(25 * mult), int(25 * mult))
            return (100, 100)
        elif "tech_" in filename.lower():
            return (188,187)
        elif "blueprint" in filename.lower():
            if "dread" in filename.lower():
                return (561,400)
            else:
                return (424,400)
        elif "name_trade_" in filename.lower():
            return (475,70)
        elif "player_layout" in filename.lower():
            return (4897,795)
        elif "classes" in folder.lower():
            return (90,33)
        elif "factionimages" in folder.lower():
            return (600,600)
        return (70, 70)

    def get_image(self, filename):
        return self.cache.get(filename)
