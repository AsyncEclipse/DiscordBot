import asyncio
import json
import discord
from discord.ui import View
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Shrine import ShrineButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
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
            if len(player[f"{tech_type}_tech"]) == 7:
                continue
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
        image = DrawHelper.show_tech_ref_image(tech_details["name"], tech_details['track'])
        await interaction.channel.send(f"{player['player_name']} acquired the tech "+tech_details["name"],file=image)
        player_helper.specifyDetailsOfAction("Researched "+tech_details["name"]+".")
        if player["science"] >= cost:  
            msg = player_helper.adjust_science(-cost)  
            game.update_player(player_helper)  
            await interaction.channel.send(msg)  
        else:  
            paid = min(cost, player["science"])   
            view = View()
            trade_value = player['trade_value']
            val = paid
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("money", discord.ButtonStyle.blurple)]: 
                if(player[resource_type] >= trade_value):
                    val += int(player[resource_type]/trade_value)
                    view.add_item(Button(label=f"Pay {trade_value} {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"FCID{player['color']}_payAtRatio_{resource_type}")) 
            if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
                emojiC = Emoji.getEmojiByName("colony_ship")
                view.add_item(Button(label=f"Get 1 Science", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForSpentResource_science"))
            view.add_item(Button(label="Done Paying", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            if val < cost:
                view2 = View()
                view2.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
                await interaction.channel.send(f"Attempted to pay a cost of {str(cost)} but you did not have enough. Please restart the turn or manually adjust resources if for some reason you should have more",view=view2)
                return
            msg = player_helper.adjust_science(-paid)  
            game.update_player(player_helper)
            if player["name"] == "Rho Indi Syndicate":
                await interaction.channel.send(
                    f"Attempted to pay a cost of {str(cost)}{msg}\n Please pay the rest of the cost by trading other "
                    f"resources at your materials ratio of 3:1 or your money ratio of 3:2"
                )
            else:
                await interaction.channel.send(
                    f"Attempted to pay a cost of {str(cost)}{msg}\n Please pay the rest of the cost by trading other resources at your trade ratio ({trade_value}:1)"
                )
            await interaction.channel.send("Payment buttons",view=view)
        
        if tech_details["art_pt"] != 0:
            view = View()
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("money", discord.ButtonStyle.blurple), ("science", discord.ButtonStyle.green)]: 
                view.add_item(Button(label=f"Gain 5 {resource_type.capitalize()}",   
                                style=button_style,   
                                custom_id=f"FCID{player['color']}_gain5resource_{resource_type}")) 
            view.add_item(Button(label="Done Gaining", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            await interaction.channel.send(  
                f"You can gain 5 of any type of resource for each artifact you have",view=view  
            )  
        if tech == "wap":
            view = View()
            seenTiles = []
            for tile in player["owned_tiles"]: 
                if tile not in seenTiles:
                    seenTiles.append(tile)
                    view.add_item(Button(label=tile,   
                                    style=discord.ButtonStyle.blurple,   
                                    custom_id=f"FCID{player['color']}_placeWarpPortal_"+tile))  
            await interaction.channel.send(  
                f"Choose which tile you would like to place the warp tile in",view=view  
            )  
        if tech_details["dtile"] != 0:
            game.addDiscTile(game.getLocationFromID(player["home_planet"]))
            await DiscoveryTileButtons.exploreDiscoveryTile(game, game.getLocationFromID(player["home_planet"]),interaction,player)
        lenTech = len(player[tech_type+"_tech"])
        if lenTech == 4 and "magDiscTileUsed" in player and not player["magDiscTileUsed"]:
            await interaction.channel.send(player["player_name"]+" due to researching your fourth tech for the first time this game as Magellan, you get a discovery tile")
            game.addDiscTile(game.getLocationFromID(player["home_planet"]))
            game.useMagDisc(str(interaction.user.id))
            await DiscoveryTileButtons.exploreDiscoveryTile(game, game.getLocationFromID(player["home_planet"]),interaction,player)

    @staticmethod  
    async def placeWarpPortal(interaction:discord.Interaction, game: GamestateHelper, player, customID):
        loc = customID.split("_")[1]
        game.addWarpPortal(loc)
        await interaction.channel.send(interaction.user.mention + " added a warp portal to tile "+loc)
        await interaction.message.delete() 

    @staticmethod  
    def calculate_cost( tech_details, tech_type,player):
        prev_tech_count = (  
            len(player[f"{tech_type}_tech"]) if tech_type != "any"  
            else max(len(player["nano_tech"]), len(player["grid_tech"]), len(player["military_tech"]))  
        )  
        track = [-8, -6, -4, -3, -2, -1, 0, 0]
        discount = track[6 - prev_tech_count]  
        for rep in player["reputation_track"]:
            if isinstance(rep, str):
                rep = rep.lower()
                if "tech discount" in rep:
                    discount -=1
        return max(tech_details["base_cost"] + discount, tech_details["min_cost"])  


    @staticmethod
    def getPlayerTotalAvailableScience(player, game):
        extra = 0
        if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
            extra +=player["colony_ships"]
        money_value = int(player["money"] / player["trade_value"])
        if player["name"] == "Rho Indi Syndicate":
            money_value = money_value * 2

        return player["science"] + money_value + int(player["materials"]/player["trade_value"])+extra

    @staticmethod  
    async def startResearch(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonCommand:bool):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        await interaction.channel.send(f"{player['player_name']} is using their turn to research")
        player_helper = PlayerHelper(interaction.user.id, player)  
        if buttonCommand:
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
                if tech_type != "any":
                    if len(player[f"{tech_type}_tech"]) == 7:
                        continue
                cost = ResearchButtons.calculate_cost(tech_details,tech_type,player)   
                tech_groups[tech_type].append((tech, tech_details["name"], cost))  
        displayedTechs = [] 
        researchedTech = player_helper.getTechs()
        for tech in researchedTech:
            displayedTechs.append(tech)
        buttonCount = 1
        avalScience = ResearchButtons.getPlayerTotalAvailableScience(player,game)
        for tech_type in tech_groups:  
            sorted_techs = sorted(tech_groups[tech_type], key=lambda x: x[2])  # Sort by cost  
            for tech, tech_name, cost in sorted_techs:  
                if cost > avalScience:
                    continue
                tech_details = tech_data.get(tech)  
                techName = "tech_"+tech_details["name"].lower().replace(" ", "_") if tech_details else tech
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
                        view.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, emoji=Emoji.getEmojiByName(techName), custom_id=f"FCID{player['color']}_getTech_{tech}_{tech_type}"))  
                    else:
                        view2.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, emoji=Emoji.getEmojiByName(techName),custom_id=f"FCID{player['color']}_getTech_{tech}_{tech_type}"))
                    buttonCount+=1
        if player["name"] == "Rho Indi Syndicate":
            await interaction.channel.send(f"{player['player_name']}, select the tech you would like to acquire. The "
                                           f"discounted cost is in parentheses. You currently have "
                                           f"{str(player['science'])} science, and can trade materials at a 3:1 "
                                           f"ratio or "
                                           f"money at 3:2 ratio.", view=view)
        else:
            await interaction.channel.send(f"{player['player_name']}, select the tech you would like to acquire. The discounted cost is in parentheses. You currently have {str(player['science'])} science, and can trade other resources for science at a {str(player['trade_value'])}:1 ratio", view=view)
        if buttonCount > 26:
            await interaction.channel.send(view=view2)
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_available_techs),ephemeral=True)
        if "shrine_in_storage" in player and len(ShrineButtons.getInitialShrineButtons(game, player).children) > 1:
            await interaction.channel.send(f"{player['player_name']} you can put down a shrine with this research action by paying its cost",view=ShrineButtons.getInitialShrineButtons(game, player))
        if buttonCommand:
            if player["research_apt"] > 1:
                if buttonCount < 25:
                    view.add_item(Button(label="Decline 2nd Tech", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
                else:
                    view2.add_item(Button(label="Decline 2nd Tech", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
                await interaction.channel.send(f"{player['player_name']}, select the second tech you would like to acquire. The discounted cost is in parentheses.", view=view)
                if buttonCount > 24:
                    await interaction.channel.send(view=view2)
            view = View()
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
            view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
            await interaction.channel.send(f"{player['player_name']} when finished you may resolve your action "
                                           f"with this button.", view=view)
            await interaction.message.delete()


    @staticmethod  
    async def getTech(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        await interaction.message.delete()  
        game = GamestateHelper(interaction.channel)  
        tech = buttonID.split("_")[1]  
        tech_type = buttonID.split("_")[2]  
        view = View()   
        player = game.get_player(interaction.user.id) 
        with open("data/techs.json", "r") as f:  
            tech_data = json.load(f)  
        tech_details = tech_data.get(tech)  
        if tech_type == "any":  
            view = await ResearchButtons.handle_wild_tech_selection(view, tech_details, tech, player)  
            await interaction.channel.send(  
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
        if trade_value > player[resource_type]:
            await interaction.channel.send(player['player_name'] + " does not have enough "+resource_type +" to trade") 
            return
        msg = player_helper.adjust_resource(resource_type,-trade_value)  
        game.update_player(player_helper)  
        await interaction.channel.send(msg)  

    @staticmethod  
    async def gain5resource(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        game = GamestateHelper(interaction.channel)  
        resource_type = buttonID.split("_")[1]   
        msg = player_helper.adjust_resource(resource_type,5)  
        game.update_player(player_helper)  
        await interaction.channel.send(msg)  
    @staticmethod  
    async def gain3resource(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        game = GamestateHelper(interaction.channel)  
        resource_type = buttonID.split("_")[1]   
        msg = player_helper.adjust_resource(resource_type,3)  
        game.update_player(player_helper)  
        await interaction.channel.send(msg)  
        await interaction.message.delete()