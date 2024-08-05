from discord.ui import View, Button
import discord
class PlayerHelper:
    def __init__(self, player_id, player_stats):
        self.stats = player_stats
        self.player_id = str(player_id)
        self.name = self.stats["player_name"]


    def adjust_materials(self, adjustment):
        before = self.stats["materials"]
        self.stats["materials"] += adjustment
        return(f"\n> Adjusted materials from {before} to {before+adjustment}")

    def adjust_science(self, adjustment):
        before = self.stats["science"]
        self.stats["science"] += adjustment
        return (f"\n> Adjusted science from {before} to {before + adjustment}")
    def adjust_resource(self, resource, adjustment):
        if(resource == "science"):
            return self.adjust_science(adjustment)
        elif resource == "materials":
            return self.adjust_materials(adjustment)
        elif resource == "money":
            return self.adjust_money(adjustment)

    def adjust_money(self, adjustment):
        before = self.stats["money"]
        self.stats["money"] += adjustment
        return(f"\n> Adjusted money from {before} to {before+adjustment}")

    def adjust_material_cube(self, adjustment):
        before = self.stats["material_pop_cubes"]
        self.stats["material_pop_cubes"] += adjustment
        return (f"\n> Adjusted material cubes from {before} to {before + adjustment}")

    def adjust_science_cube(self, adjustment):
        before = self.stats["science_pop_cubes"]
        self.stats["science_pop_cubes"] += adjustment
        return (f"\n> Adjusted science cubes from {before} to {before + adjustment}")

    def adjust_money_cube(self, adjustment):
        before = self.stats["money_pop_cubes"]
        self.stats["money_pop_cubes"] += adjustment
        return (f"\n> Adjusted money cubes from {before} to {before + adjustment}")
    def adjust_influence(self, adjustment):
        before = self.stats["influence_discs"]
        self.stats["influence_discs"] += adjustment
        return (f"\n> Adjusted influence discs from {before} to {before + adjustment}")
    def spend_influence_on_action(self, action):
        self.adjust_influence(-1)
        if action+"_action_counters" not in self.stats:
            self.stats[action+"_action_counters"] = 0
        self.stats[action+"_action_counters"] = self.stats[action+"_action_counters"]+1
        
    def passTurn(self):
        self.stats["passed"] = True

    def adjust_colony_ships(self, adjustement):
        if self.stats["colony_ships"] <= 0:
            return False
        elif (self.stats["colony_ships"] - adjustement) < 0:
            return False
        else:
            return(self.stats["colony_ships"] - adjustement)
    @staticmethod  
    def getStartTurnButtons(p1):
        view = View()  
        view.add_item(Button(label=f"Explore ({p1['explore_apt']})", style=discord.ButtonStyle.success, custom_id="startExplore"))  
        view.add_item(Button(label=f"Research ({p1['research_apt']})", style=discord.ButtonStyle.primary, custom_id="startResearch"))  
        view.add_item(Button(label=f"Build ({p1['build_apt']})", style=discord.ButtonStyle.success, custom_id="startBuild"))  
        view.add_item(Button(label=f"Upgrade ({p1['upgrade_apt']})", style=discord.ButtonStyle.primary, custom_id="startUpgrade"))  
        view.add_item(Button(label=f"Move ({p1['move_apt']})", style=discord.ButtonStyle.success, custom_id="startMove"))  
        view.add_item(Button(label=f"Influence ({p1['influence_apt']})", style=discord.ButtonStyle.secondary, custom_id="startInfluence"))  
        view.add_item(Button(label="Pass", style=discord.ButtonStyle.danger, custom_id="passForRound"))  
        return view
    
    def materials_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["material_pop_cubes"]
        return(track[cubes])

    def science_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["science_pop_cubes"]
        return(track[cubes])

    def money_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["money_pop_cubes"]
        return(track[cubes])

    def upkeep(self):
        track = self.stats["influence_track"]
        discs = self.stats["influence_discs"]
        if discs >= 13:
            return(0)
        else:
            return(track[discs])