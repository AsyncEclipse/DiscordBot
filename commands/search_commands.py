import asyncio
from collections import Counter
import os
import discord
import json
from discord.ext import commands
from discord import app_commands
import config
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper


class SearchCommands(commands.GroupCog, name="search"):
    def __init__(self, bot):
        self.bot = bot

    tech_choices_a_n = [
        app_commands.Choice(name="Absorption Shield", value="abs"),
        app_commands.Choice(name="Advanced Economy", value="ade"),
        app_commands.Choice(name="Advanced Labs", value="adl"),
        app_commands.Choice(name="Advanced Mining", value="adm"),
        app_commands.Choice(name="Advanced Robotics", value="adr"),
        app_commands.Choice(name="Antimatter Cannon", value="anc"),
        app_commands.Choice(name="Ancient Labs", value="anl"),
        app_commands.Choice(name="Antimatter Splitter", value="ans"),
        app_commands.Choice(name="Artifact Key", value="ark"),
        app_commands.Choice(name="Cloaking Device", value="cld"),
        app_commands.Choice(name="Conifold Field", value="cof"),
        app_commands.Choice(name="Flux Missile", value="flm"),
        app_commands.Choice(name="Fusion Drive", value="fud"),
        app_commands.Choice(name="Fusion Source", value="fus"),
        app_commands.Choice(name="Gauss Shield", value="gas"),
        app_commands.Choice(name="Gluon Computer", value="glc"),
        app_commands.Choice(name="Improved Hull", value="imh"),
        app_commands.Choice(name="Improved Logistics", value="iml"),
        app_commands.Choice(name="Metasynthesis", value="met"),
        app_commands.Choice(name="Monolith", value="mon"),
        app_commands.Choice(name="Nano Robots", value="nar"),
        app_commands.Choice(name="Neutron Absorber", value="nea"),
        app_commands.Choice(name="Neutron Bombs", value="neb")]
    tech_choices_o_z = [
        app_commands.Choice(name="Orbital", value="orb"),
        app_commands.Choice(name="Phase Shield", value="phs"),
        app_commands.Choice(name="Pico Modulator", value="pim"),
        app_commands.Choice(name="Plasma Cannon", value="plc"),
        app_commands.Choice(name="Plasma Missile", value="plm"),
        app_commands.Choice(name="Positron Computer", value="poc"),
        app_commands.Choice(name="Quantum Grid", value="qug"),
        app_commands.Choice(name="Rift Cannon", value="rican"),
        app_commands.Choice(name="Sentient Hull", value="seh"),
        app_commands.Choice(name="Soliton Cannon", value="socan"),
        app_commands.Choice(name="Star Base", value="stb"),
        app_commands.Choice(name="Tachyon Drive", value="tad"),
        app_commands.Choice(name="Tachyon Source", value="tas"),
        app_commands.Choice(name="Transition Drive", value="trd"),
        app_commands.Choice(name="Warp Portal", value="wap"),
        app_commands.Choice(name="Wormhole Generator", value="wog"),
        app_commands.Choice(name="Zero Point Source", value="zes")]
    part_choices_a_m = [
        app_commands.Choice(name="Absorption Shield", value="abs"),
        app_commands.Choice(name="Antimatter Cannon", value="anc"),
        app_commands.Choice(name="Antimatter Missile", value="anm"),
        app_commands.Choice(name="Axion Computer", value="axc"),
        app_commands.Choice(name="Conformal Drive", value="cod"),
        app_commands.Choice(name="Conifold Field", value="cof"),
        app_commands.Choice(name="Electron Computer", value="elc"),
        app_commands.Choice(name="Flux Missile", value="flm"),
        app_commands.Choice(name="Flux Shield", value="fls"),
        app_commands.Choice(name="Fusion Drive", value="fud"),
        app_commands.Choice(name="Fusion Source", value="fus"),
        app_commands.Choice(name="Gauss Shield", value="gas"),
        app_commands.Choice(name="Gluon Computer", value="glc"),
        app_commands.Choice(name="Hull", value="hul"),
        app_commands.Choice(name="Hypergrid Source", value="hyg"),
        app_commands.Choice(name="Improved Hull", value="imh"),
        app_commands.Choice(name="Inversion Shield", value="ins"),
        app_commands.Choice(name="Ion Cannon", value="ioc"),
        app_commands.Choice(name="Ion Disruptor", value="iod"),
        app_commands.Choice(name="Ion Missile", value="iom"),
        app_commands.Choice(name="Ion Turret", value="iot"),
        app_commands.Choice(name="Jump Drive", value="jud"),
        app_commands.Choice(name="Morph Shield", value="mos"),
        app_commands.Choice(name="Muon Source", value="mus")]
    part_choices_n_z = [
        app_commands.Choice(name="Nonlinear Drive", value="nod"),
        app_commands.Choice(name="Nuclear Drive", value="nud"),
        app_commands.Choice(name="Nuclear Source", value="nus"),
        app_commands.Choice(name="Phase Shield", value="phs"),
        app_commands.Choice(name="Plasma Cannon", value="plc"),
        app_commands.Choice(name="Plasma Missile", value="plm"),
        app_commands.Choice(name="Plasma Turret", value="plt"),
        app_commands.Choice(name="Positron Computer", value="poc"),
        app_commands.Choice(name="Rift Cannon", value="rican"),
        app_commands.Choice(name="Rift Conductor", value="ricon"),
        app_commands.Choice(name="Sentient Hull", value="seh"),
        app_commands.Choice(name="Shard Hull", value="shh"),
        app_commands.Choice(name="Soliton Cannon", value="socan"),
        app_commands.Choice(name="Soliton Charger", value="socha"),
        app_commands.Choice(name="Soliton Missile", value="som"),
        app_commands.Choice(name="Tachyon Drive", value="tad"),
        app_commands.Choice(name="Tachyon Source", value="tas"),
        app_commands.Choice(name="Transition Drive", value="trd"),
        app_commands.Choice(name="Zero Point Source", value="zes")]
    disc_tiles_ancient_ship_parts_choices = [
        app_commands.Choice(name="Antimatter Missile", value="anm"),
        app_commands.Choice(name="Axion Computer", value="acx"),
        app_commands.Choice(name="Conformal Drive", value="cod"),
        app_commands.Choice(name="Flux Shield", value="fls"),
        app_commands.Choice(name="Hypergrid Source", value="hyg"),
        app_commands.Choice(name="Inversion Shield", value="ins"),
        app_commands.Choice(name="Ion Disruptor", value="iod"),
        app_commands.Choice(name="Ion Missile", value="iom"),
        app_commands.Choice(name="Ion Turret", value="iot"),
        app_commands.Choice(name="Jump Drive", value="jud"),
        app_commands.Choice(name="Morph Shield", value="mos"),
        app_commands.Choice(name="Muon Source", value="mus"),
        app_commands.Choice(name="Nonlinear Drive", value="nod"),
        app_commands.Choice(name="Plasma Turret", value="plt"),
        app_commands.Choice(name="Shard Hull", value="shh"),
        app_commands.Choice(name="Soliton Charger", value="socha"),
        app_commands.Choice(name="Soliton Missile", value="som"),
        app_commands.Choice(name="Rift Conductor", value="ricon")]
    discovery_tiles_other_choices = [
        app_commands.Choice(name="All Income Gain", value="all"),
        app_commands.Choice(name="Artifact Codex", value="art"),
        app_commands.Choice(name="Ancient Cruiser", value="cru"),
        app_commands.Choice(name="Ancient Might", value="rep"),
        app_commands.Choice(name="Material Gain", value="mat"),
        app_commands.Choice(name="Money and Wild Gain", value="mix"),
        app_commands.Choice(name="Money Gain", value="mog"),
        app_commands.Choice(name="Monolith", value="mon"),
        app_commands.Choice(name="Orbital", value="orb"),
        app_commands.Choice(name="Science Gain", value="sci"),
        app_commands.Choice(name="Tech Gain", value="tec"),
        app_commands.Choice(name="Warp Portal", value="wap")]
    community_part_choices = [
        app_commands.Choice(name="Improved Hull mod", value="imhmod"),
        app_commands.Choice(name="Phase Shield mod", value="phsmod")
    ]

    @app_commands.command(name="upgrade_reference")
    async def upgrade_reference(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        image = DrawHelper.show_ref("upgrade")
        await interaction.followup.send(file=image, ephemeral=True)

    @app_commands.command(name="tech_a_to_n", description="Tech information A through N")
    @app_commands.choices(tech_choice=tech_choices_a_n)
    async def tech_a_to_n(self, interaction: discord.Interaction, tech_choice: app_commands.Choice[str]):
        with open("data/techs.json", "r") as f:
            data = json.load(f)
        tech_info = data[tech_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_tech_ref_image(tech_choice.name, tech_info['track'])
        await interaction.followup.send(f"{tech_info['name']}"
                                        f"\n> Base Cost: {tech_info['base_cost']}"
                                        f"\n> Min Cost: {tech_info['min_cost']}"
                                        f"\n> Tech track: {tech_info['track']}"
                                        f"\n> Total number: {tech_info['num']}"
                                        f"\n> Description: {tech_info['description']}"
                                        f"\n> Reference Code: {tech_choice.value}",
                                        file=image)

    @app_commands.command(name="tech_o_to_z", description="Tech information O through Z")
    @app_commands.choices(tech_choice=tech_choices_o_z)
    async def tech_o_to_z(self, interaction: discord.Interaction, tech_choice: app_commands.Choice[str]):
        with open("data/techs.json", "r") as f:
            data = json.load(f)
        tech_info = data[tech_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_tech_ref_image(tech_choice.name, tech_info['track'])
        await interaction.followup.send(f"{tech_info['name']}"
                                        f"\n> Base Cost: {tech_info['base_cost']}"
                                        f"\n> Min Cost: {tech_info['min_cost']}"
                                        f"\n> Tech track: {tech_info['track']}"
                                        f"\n> Total number: {tech_info['num']}"
                                        f"\n> Description: {tech_info['description']}"
                                        f"\n> Reference Code: {tech_choice.value}",
                                        file=image)

    @app_commands.command(name="parts_a_to_m", description="Part information A through M")
    @app_commands.choices(part_choice=part_choices_a_m)
    async def parts_a_to_m(self, interaction: discord.Interaction, part_choice: app_commands.Choice[str]):
        with open("data/parts.json", "r") as f:
            data = json.load(f)
        part_info = data[part_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_part_ref_image(part_choice.name)
        await interaction.followup.send(f"{part_info['name']}"
                                        f"\n> Energy Cost: {part_info['nrg_use']}"
                                        f"\n> Initiative: {part_info['speed']}"
                                        f"\n> Description: {part_info['description']}"
                                        f"\n> Reference Code: {part_choice.value}",
                                        file=image)

    @app_commands.command(name="parts_n_to_z", description="Part information N through Z")
    @app_commands.choices(part_choice=part_choices_n_z)
    async def parts_n_to_z(self, interaction: discord.Interaction, part_choice: app_commands.Choice[str]):
        with open("data/parts.json", "r") as f:
            data = json.load(f)
        part_info = data[part_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_part_ref_image(part_choice.name)
        await interaction.followup.send(f"{part_info['name']}"
                                        f"\n> Energy Cost: {part_info['nrg_use']}"
                                        f"\n> Initiative: {part_info['speed']}"
                                        f"\n> Description: {part_info['description']}"
                                        f"\n> Reference Code: {part_choice.value}",
                                        file=image)

    @app_commands.command(name="community_parts", description="Community balanced parts")
    @app_commands.choices(part_choice=community_part_choices)
    async def community_parts(self, interaction: discord.Interaction, part_choice: app_commands.Choice[str]):
        with open("data/parts.json", "r") as f:
            data = json.load(f)
        part_info = data[part_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_part_ref_image(part_choice.name)
        await interaction.followup.send(f"{part_info['name']}"
                                        f"\n> Energy Cost: {part_info['nrg_use']}"
                                        f"\n> Initiative: {part_info['speed']}"
                                        f"\n> Description: {part_info['description']}"
                                        f"\n> Reference Code: {part_choice.value}",
                                        file=image)

    @app_commands.command(name="ancient_disc_tiles", description="Ancient part disc tiles")
    @app_commands.choices(tile_choice=disc_tiles_ancient_ship_parts_choices)
    async def ancient_disc_tiles(self, interaction: discord.Interaction, tile_choice: app_commands.Choice[str]):
        with open("data/discoverytiles.json", "r") as f:
            data = json.load(f)
        tile_info = data[tile_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_disc_tile_ref_image(tile_choice.name)
        await interaction.followup.send(f"{tile_info['name']}"
                                        f"\n> Total Available: {tile_info['num']}"
                                        f"\n> Description: {tile_info['description']}"
                                        f"\n> Reference Code: {tile_choice.value}",
                                        file=image)

    @app_commands.command(name="discovery_tiles", description="Non ancient discovery tiles")
    @app_commands.choices(tile_choice=discovery_tiles_other_choices)
    async def discovery_tiles(self, interaction: discord.Interaction, tile_choice: app_commands.Choice[str]):
        with open("data/discoverytiles.json", "r") as f:
            data = json.load(f)
        tile_info = data[tile_choice.value]
        await interaction.response.defer(thinking=True)
        image = DrawHelper.show_disc_tile_ref_image(tile_choice.name)
        await interaction.followup.send(f"{tile_info['name']}"
                                        f"\n> Total Available: {tile_info['num']}"
                                        f"\n> Description: {tile_info['description']}"
                                        f"\n> Reference Code: {tile_choice.value}",
                                        file=image)
        

    @app_commands.command(name="draft_stats", description="Stats for the drafted factions")
    async def stats(self, interaction: discord.Interaction, tourney_only:bool=False):
        userID = str(interaction.user.id)
        if userID != "488681163146133504" and userID != "265561667293675521":
            await interaction.response.send_message("You are not authorised to use this command.")
            return
        total_faction_drafts = Counter()    
        round_count = Counter() 
        vp_count = Counter()
        from collections import defaultdict  

        scores_dict = defaultdict(list)  
        finished_tourney_games = Counter()
        faction_victory_count = Counter()
        faction_performance = Counter()
        max_faction_performance = Counter()
        relative_faction_performance = Counter()
        positional_drafts = [Counter() for _ in range(6)] 
        await interaction.response.defer(thinking=True)
        await interaction.followup.send("Here are your stats")
        lowerLim = 100
        higherLim = 999
        gameSumString = ""
        gameFactionString = ""
        if tourney_only:
            higherLim = 504
            lowerLim = 478
        for x in range(lowerLim, higherLim):
            gameName = f"aeb{x}"
            if not os.path.exists(f"{config.gamestate_path}/{gameName}.json"):
                continue
            game = GamestateHelper(None, gameName)
            drawing = DrawHelper(game.gamestate)
            if "draftedFactions" not in game.gamestate:
                continue
        
            for position, idNFaction in enumerate(game.gamestate['draftedFactions']):  
                faction = idNFaction[1]
                total_faction_drafts[faction] += 1  
                positional_drafts[position][faction] += 1  
            if tourney_only:
                if "roundNum" not in game.gamestate:
                    continue
                else:
                    round_count["Round "+str(game.gamestate["roundNum"])] +=1
                if game.gamestate["roundNum"] != 9:
                    continue
                gameSumString += f"{gameName}:   "
                gameFactionString += f"{gameName}:   "
                if game.gamestate.get("5playerhyperlane"):
                    gameSumString += "(Hyperlane)   "
                    gameFactionString += "(5p Hyperlane)   "
                highestVP = 1
                secondVP = 1
                for player in game.gamestate["players"]:
                    if drawing.get_public_points(game.gamestate["players"][player], True) >= highestVP:
                        secondVP = highestVP
                        highestVP = drawing.get_public_points(game.gamestate["players"][player], True)
                    else:
                        if drawing.get_public_points(game.gamestate["players"][player], True) >= secondVP:
                            secondVP = drawing.get_public_points(game.gamestate["players"][player], True)
                for player in game.gamestate["players"]:
                    username = game.gamestate["players"][player]["username"]
                    if "(" in username:
                        username = username.split("(")[0].replace(" ","")
                    bonus = 0
                    normalVP = round(float(100.0*drawing.get_public_points(game.gamestate["players"][player], True)/highestVP),2)
                    if drawing.get_public_points(game.gamestate["players"][player], True) == highestVP:
                        if highestVP > secondVP + 4:
                            bonus = 10
                        if highestVP > secondVP + 9:
                            bonus = 20
                        bonus = 0
                    vp_count[username] += normalVP + bonus
                    gameSumString += f"{username}: {str(drawing.get_public_points(game.gamestate['players'][player], True))}    "
                    gameFactionString += f"{game.gamestate['players'][player]['name']}: {str(drawing.get_public_points(game.gamestate['players'][player], True))}    "
                    if game.gamestate["roundNum"] == 9:
                        finished_tourney_games[username] += 1
                    else:
                        finished_tourney_games[username] += 0
                if game.gamestate["roundNum"] == 9:
                    winner, highestScore, faction = game.getWinner()
                    if "Terran" in faction:
                        faction = "Terran"
                    faction_victory_count[faction] += 1
                    for player in game.gamestate["players"]:
                        factionVP = drawing.get_public_points(game.gamestate["players"][player], True)
                        faction = game.gamestate["players"][player]["name"]
                        if "Terran" in faction:
                            faction = "Terran"
                        faction_performance[faction] += int(100*factionVP/highestScore)
                        max_faction_performance[faction] +=100
                gameSumString += "\n"
                gameFactionString += "\n"
        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)
        await interaction.followup.send("Total Faction Draft Counts:")  
        summary = ""
        for faction, count in total_faction_drafts.most_common():  
            summary += f"{faction_data[faction]['name']}: {count}\n"
        await interaction.channel.send(summary)  
        
        # await interaction.channel.send("\nPositional Faction Draft Counts:")  
        # for position, counter in enumerate(positional_drafts, 1):  
        #     await interaction.channel.send(f"\nPosition {position}:")  
        #     for faction, count in counter.most_common():  
        #         await interaction.channel.send(f"{faction_data[faction]['name']}: {count}") 
        async def send_long_message(interaction, message):  
            chunks = [message[i:i+1990] for i in range(0, len(message), 1990)]  
            for chunk in chunks:  
                await interaction.channel.send(chunk) 
        if tourney_only:
            summary = "Round Progression:\n"
            for roundN, count in round_count.most_common():  
                summary += f"{roundN}: {count} games\n"
            asyncio.create_task(interaction.channel.send(summary) )
            summary = "Point Progression:\n"
            rank = 1
            for username, count in vp_count.most_common():  
                summary += f"{rank}. {username}: {round(count,2)}/360 VPs ({str(finished_tourney_games[username])} games)\n"
                rank += 1
            asyncio.create_task(interaction.channel.send(summary) )
            summary = "Faction Wins:\n"
            for faction, count in faction_victory_count.most_common():  
                summary += f"{faction}: {count} wins\n"
            asyncio.create_task(interaction.channel.send(summary) )
            summary = "Faction Performance:\n"
            for faction, count in faction_performance.most_common():
                relative_faction_performance[faction] += int(count/max_faction_performance[faction] * 100)
            for faction, count in relative_faction_performance.most_common():  
                summary += f"{faction}: {count} out of 100 possible points (in {str(int(max_faction_performance[faction]/100))} games)\n"
            asyncio.create_task(send_long_message(interaction, gameSumString))
            asyncio.create_task(send_long_message(interaction, gameFactionString))
    
