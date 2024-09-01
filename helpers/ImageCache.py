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
                    image_path = os.path.join(root, filename)  
                    size = self.get_image_size(root, filename)  
                    if "wh_mask" in filename:
                        self.cache[filename] = Image.open(image_path).convert("RGBA").resize(size).rotate(180)
                    else:  
                        self.cache[filename] = Image.open(image_path).convert("RGBA").resize(size)
    #any(substring in main_string for substring in substrings)
    def get_image_size(self, folder, filename):  
        if "hexes" in folder.lower():  
            return (345,299)  
        elif "masks" in folder.lower():  
            if "banner" in filename.lower():
                return (98, 48)  
            elif "hsMask" in filename.lower():
                return (70,70)
            else:
                return (42,22)  
        elif "factions" in folder.lower():  
            return (895, 500)
        elif "all_boards" in folder.lower():  
            if "popcube" in filename.lower():
                return (30,30)
            elif "influence_disc" in filename.lower():
                return (40,40)
            elif "reputation" in filename.lower():
                return (58,58)
            elif "colony_ship" in filename.lower():
                return (100,100)
            elif "points" in filename.lower():
                return (80,80)
        elif "basic_ships" in folder.lower():  
            if any(substring in filename.lower() for substring in ["gcds", "gcdsadv", "anc", "ancadv", "grd", "grdadv"]):
                return (110,110)
            else:
                return (70,70) 
        elif "discovery_tiles" in folder.lower():  
            return (80, 80)  
        elif "upgrades" in folder.lower():  
            return (58,58)  
        elif "resourcesymbol" in folder.lower():  
            return (100,100)  
        elif "tech_" in filename.lower():  
            return (68, 68)   
        return (70, 70)

    def get_image(self, filename):  
        return self.cache.get(filename)  