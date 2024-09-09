import json
import discord
from discord.ui import View
from Buttons.DiscoveryTile import DiscoveryTileButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button

class ResearchButtons:

    @staticmethod  
    async def handle_wild_tech_selection(view:View, tech_details, tech,player):
        for tech_type, button_style in [("grid", discord.ButtonStyle.green),   
                                        ("nano", discord.ButtonStyle.blurple),   
                                        ("military", discord.ButtonStyle.red)]:  
            cost = ResearchButtons.calculate_cost(tech_details, tech_type,player)  
            view.add_item(Button(label=f"{tech_type.capitalize()} ({cost})",   
                                style=button_style,   
                                custom_id=f"FCID{player['color']}_getTech_{tech}_{tech_type}"))  
        return view
    @staticmethod  
    async def handle_specific_tech_selection(interaction:discord.Interaction, game: GamestateHelper, player, tech_details, tech_type, tech):
        cost = ResearchButtons.calculate_cost(tech_details, tech_type,player)  
        game.playerResearchTech(str(interaction.user.id), tech, tech_type)  
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)  
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)  
        tech_details = tech_data.get(tech)
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send(f"{interaction.user.mention} acquired the tech "+tech_details["name"],file=drawing.show_specific_tech(tech))
        if player["science"] >= cost:  
            msg = player_helper.adjust_science(-cost)  
            game.update_player(player_helper)  
            await interaction.response.send_message(msg)  
        else:  
            paid = min(cost, player["science"])  
            msg = player_helper.adjust_science(-paid)  
            game.update_player(player_helper)  
            view = View()
            trade_value = player['trade_value']
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("money", discord.ButtonStyle.blurple)]: 
                if(player[resource_type] >= trade_value):
                    view.add_item(Button(label=f"Pay {trade_value} {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"FCID{player['color']}_payAtRatio_{resource_type}")) 
            view.add_item(Button(label="Done Paying", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            await interaction.response.send_message(  
                f"Attempted to pay a cost of {str(cost)}\n{msg}\n Please pay the rest of the cost by trading other resources at your trade ratio ({trade_value}:1)",view=view  
            )  
        
        if tech_details["art_pt"] != 0:
            view = View()
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("money", discord.ButtonStyle.blurple), ("science", discord.ButtonStyle.green)]: 
                if(player[resource_type] >= trade_value):
                    view.add_item(Button(label=f"Gain 5 {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"gain5resource_{resource_type}")) 
            view.add_item(Button(label="Done Gaining", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            await interaction.response.send_message(  
                f"You can gain 5 of any type of resource for each artifact you have",view=view  
            )  
        if tech_details["dtile"] != 0:
            await DiscoveryTileButtons.exploreDiscoveryTile(game, game.getLocationFromID(player["home_planet"]),interaction,player)

    @staticmethod  
    def calculate_cost( tech_details, tech_type,player):
        prev_tech_count = (  
            len(player[f"{tech_type}_tech"]) if tech_type != "any"  
            else max(len(player["nano_tech"]), len(player["grid_tech"]), len(player["military_tech"]))  
        )  
        discount = player["tech_track"][6 - prev_tech_count]  
        return max(tech_details["base_cost"] + discount, tech_details["min_cost"])  

    @staticmethod  
    async def startResearch(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonCommand:bool):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)  
        player_helper.spend_influence_on_action("research")
        game.update_player(player_helper)
        player = game.get_player(interaction.user.id) 
        drawing = DrawHelper(game.gamestate)  
        view = View()
        view2 = View()
        techsAvailable = game.get_gamestate()["available_techs"]  
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
                cost = ResearchButtons.calculate_cost(tech_details,tech_type,player)   
                tech_groups[tech_type].append((tech, tech_details["name"], cost))  
        displayedTechs = [] 
        buttonCount = 1
        for tech_type in tech_groups:  
            sorted_techs = sorted(tech_groups[tech_type], key=lambda x: x[2])  # Sort by cost  
            for tech, tech_name, cost in sorted_techs:  
                buttonStyle = discord.ButtonStyle.red  
                if tech_type == "grid":  
                    buttonStyle = discord.ButtonStyle.green  
                elif tech_type == "nano":  
                    buttonStyle = discord.ButtonStyle.blurple  
                elif tech_type == "any":  
                    buttonStyle = discord.ButtonStyle.gray  
                if(tech not in displayedTechs):
                    displayedTechs.append(tech)
                    if buttonCount < 26:
                        view.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, custom_id=f"FCID{player['color']}_getTech_{tech}_{tech_type}"))  
                    else:
                        view2.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, custom_id=f"FCID{player['color']}_getTech_{tech}_{tech_type}"))
                    buttonCount+=1
        await interaction.response.send_message(f"{interaction.user.mention}, select the tech you would like to acquire. The discounted cost is in parentheses.", view=view)
        if buttonCount > 26:
            await interaction.channel.send(view=view2)
        await interaction.followup.send(file=drawing.show_available_techs(),ephemeral=True)
        if buttonCommand:
            if player["research_apt"] > 1:
                view.add_item(Button(label="Decline 2nd Tech", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
                await interaction.channel.send(f"{interaction.user.mention}, select the second tech you would like to acquire. The discounted cost is in parentheses.", view=view)
                if buttonCount > 26:
                    await interaction.channel.send(view=view2)
            view = View()
            view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
            await interaction.channel.send(f"{interaction.user.mention} when you're finished resolving your action, you may end turn with this button.", view=view)

    @staticmethod  
    async def getTech(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction):
        await interaction.message.delete()  
        game = GamestateHelper(interaction.channel)  
        buttonID = interaction.data["custom_id"].split("_")  
        tech = buttonID[1]  
        tech_type = buttonID[2]  
        view = View()   
        player = game.get_player(interaction.user.id) 
        with open("data/techs.json", "r") as f:  
            tech_data = json.load(f)  
        tech_details = tech_data.get(tech)  
        if tech_type == "any":  
            view = await ResearchButtons.handle_wild_tech_selection(view, tech_details, tech, player)  
            await interaction.response.send_message(  
                f"{interaction.user.mention}, select the row of tech you would like to place this wild tech in. The discounted cost is in parentheses.",   
                view=view  
            )  
        else:  
            await ResearchButtons.handle_specific_tech_selection(interaction, game, player, tech_details, tech_type,tech)
            
    @staticmethod  
    async def payAtRatio(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction,  buttonID:str):
        game = GamestateHelper(interaction.channel)  
        resource_type = buttonID.split("_")[1]
        trade_value = player["trade_value"]
        paid = min(trade_value, player[resource_type])  
        msg = player_helper.adjust_resource(resource_type,-paid)  
        game.update_player(player_helper)  
        await interaction.response.send_message(msg)  

    @staticmethod  
    async def gain5resource(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        game = GamestateHelper(interaction.channel)  
        resource_type = buttonID.split("_")[1]   
        msg = player_helper.adjust_resource(resource_type,5)  
        game.update_player(player_helper)  
        await interaction.response.send_message(msg)  