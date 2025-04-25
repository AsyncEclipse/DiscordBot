import asyncio
import discord
from Buttons.Draft import DraftButtons
import config
from discord.ext import commands
from discord import app_commands
from typing import Optional
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper


class SetupCommands(commands.GroupCog, name="setup"):
    def __init__(self, bot):
        self.bot = bot
    ai_choices = [app_commands.Choice(name="Default", value="def"),
                  app_commands.Choice(name="Advanced", value="adv"),
                  app_commands.Choice(name="Worlds Apart", value="wa"),
                  app_commands.Choice(name="Random And Seperate", value="random")]

    ai_choices2 = [app_commands.Choice(name="Default", value="def"),
                  app_commands.Choice(name="Advanced", value="adv"),
                  app_commands.Choice(name="Worlds Apart", value="wa")]

    ai_ship_choices = [app_commands.Choice(name="GCDS", value="gcds"),
                  app_commands.Choice(name="Ancient", value="anc"),
                  app_commands.Choice(name="Guardian", value="grd")]

    factionChoices = [app_commands.Choice(name="Hydran Progress", value="hyd"),
                      app_commands.Choice(name="Eridani Empire", value="eri"),
                      app_commands.Choice(name="Orion Hegemony", value="ori"),
                      app_commands.Choice(name="Descendants of Draco", value="dra"),
                      app_commands.Choice(name="Mechanema", value="mec"),
                      app_commands.Choice(name="Planta", value="pla"),
                      app_commands.Choice(name="Wardens of Magellan", value="mag"),
                      app_commands.Choice(name="Enlightened of Lyra", value="lyr"),
                      app_commands.Choice(name="Rho Indi Syndicate", value="rho"),
                      app_commands.Choice(name="The Exiles", value="exl"),
                      app_commands.Choice(name="Terran Alliance (Orion)", value="ter1"),
                      app_commands.Choice(name="Terran Conglomerate (Mech)", value="ter2"),
                      app_commands.Choice(name="Terran Directorate (Eridani)", value="ter3"),
                      app_commands.Choice(name="Terran Federation (Hydran)", value="ter4"),
                      app_commands.Choice(name="Terran Republic (Draco)", value="ter5"),
                      app_commands.Choice(name="Terran Union (Planta)", value="ter6"),]
    
    @app_commands.choices(ai_ship_type=ai_choices2)
    @app_commands.choices(ai_ship=ai_ship_choices)
    @app_commands.command(name="ai_ships")
    async def ai_ships(self, interaction: discord.Interaction, ai_ship:app_commands.Choice[str], ai_ship_type:app_commands.Choice[str]):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer()
        game.changeShip(ai_ship.value, ai_ship_type.value)
        await interaction.followup.send("Successfully changed the AI "+ai_ship.name+" to have "+ai_ship_type.name + " stats")

    

    @app_commands.command(name="game")
    @app_commands.choices(faction1=factionChoices, faction2=factionChoices, faction3=factionChoices,
                          faction4=factionChoices, faction5=factionChoices, faction6=factionChoices,faction7=factionChoices,faction8=factionChoices,faction9=factionChoices)
    async def game(self, interaction: discord.Interaction,
                   player1: discord.Member, faction1: app_commands.Choice[str],
                   player2: discord.Member, faction2: app_commands.Choice[str],
                   player3: Optional[discord.Member] = None, faction3: Optional[app_commands.Choice[str]] = None,
                   player4: Optional[discord.Member] = None, faction4: Optional[app_commands.Choice[str]] = None,
                   player5: Optional[discord.Member] = None, faction5: Optional[app_commands.Choice[str]] = None,
                   player6: Optional[discord.Member] = None, faction6: Optional[app_commands.Choice[str]] = None,
                   player7: Optional[discord.Member] = None, faction7: Optional[app_commands.Choice[str]] = None,
                   player8: Optional[discord.Member] = None, faction8: Optional[app_commands.Choice[str]] = None,
                   player9: Optional[discord.Member] = None, faction9: Optional[app_commands.Choice[str]] = None,):

        temp_player_list = [player1, player2, player3, player4, player5, player6,player7, player8,player9]
        temp_playerID_list = []
        temp_factionID_list = []
        for player in temp_player_list:
            if player is not None:
                temp_playerID_list.append(player.id)
        temp_faction_list = [faction1, faction2, faction3, faction4, faction5, faction6, faction7, faction8, faction9]
        for faction in temp_faction_list:
            if faction is not None:
                temp_factionID_list.append(faction.value)
        game = GamestateHelper(interaction.channel)
        await DraftButtons.generalSetup(interaction, game, temp_playerID_list, temp_factionID_list)

    @app_commands.command(name="set_turn_order")
    async def set_turn_order(self, interaction: discord.Interaction,
                             player1: discord.Member,
                             player2: discord.Member,
                             player3: Optional[discord.Member] = None,
                             player4: Optional[discord.Member] = None,
                             player5: Optional[discord.Member] = None,
                             player6: Optional[discord.Member] = None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        game = GamestateHelper(interaction.channel)
        player_list = []
        for i in temp_player_list:
            if i is not None:
                player = game.get_player(i.id)
                player_list.append(player["player_name"])
        game.setTurnOrder(player_list)
        await interaction.response.send_message("Successfully set turn order")

    @app_commands.command(name="add_players")
    async def add_players(self, interaction: discord.Interaction, game_aeb_name: str,
                          player1: discord.Member,
                          player2: Optional[discord.Member] = None,
                          player3: Optional[discord.Member] = None,
                          player4: Optional[discord.Member] = None,
                          player5: Optional[discord.Member] = None):
        temp_player_list = [player1, player2, player3, player4, player5]
        player_list = []
        await interaction.response.defer(thinking=False)
        for i in temp_player_list:
            if i is not None:
                player_list.append([i.id, i.name])
        if "aeb" not in game_aeb_name:
            await interaction.channel.send("Please provide a valid game name,"
                                           " it will have the format of aebXXX,"
                                           " where XXX is a number")
            return
        game = GamestateHelper(None, game_aeb_name)
        game.addPlayers(player_list)

        async def get_or_create_role(guild: discord.Guild, role_name):
            for role in guild.roles:
                if role.name == role_name:
                    return role
            return await guild.create_role(name=role_name, mentionable=True)
        role = await get_or_create_role(interaction.guild, game_aeb_name)

        for player_id in player_list:
            member = interaction.guild.get_member(player_id[0])
            if member:
                await member.add_roles(role)
        await interaction.channel.send("Successfully Added Players")

    @app_commands.choices(ai_ship_type=ai_choices)
    @app_commands.command(name="create_new_game",
                          description="Start the game setup. Also, choose which expansions to use.")
    async def create_new_game(self, interaction: discord.Interaction, game_name: str,
                              player1: discord.Member,
                              player_count: int,
                              player2: Optional[discord.Member] = None,
                              player3: Optional[discord.Member] = None,
                              player4: Optional[discord.Member] = None,
                              player5: Optional[discord.Member] = None,
                              player6: Optional[discord.Member] = None,
                              player7: Optional[discord.Member] = None,
                              player8: Optional[discord.Member] = None,
                              player9: Optional[discord.Member] = None,
                              ai_ship_type: Optional[app_commands.Choice[str]] = None,
                              rift_cannon: Optional[bool] = True,
                              turn_order_variant: Optional[bool] = True,
                              galactic_event_tiles: Optional[bool] = False,
                              hyperlanes: Optional[bool] = False,
                              community_parts: Optional[bool] = False,
                              ban_factions: Optional[bool] = False):
        """
        :param ai_ship_type: Choose which type of AI ships to use.
        :param rift_cannon: Rift cannons are enabled by default.
        :param turn_order_variant: Pass turn order is enabled by default.
        :param galactic_event_tiles: Supernova/black-holes/Pulsars are disabled by default.
        :param hyperlanes: Hyperlanes for 4p and 5p are default off.
        :param ban_factions: Used to ban 10-playerCount factions from the draft.
        :param community_parts: Turns on commnity changes to improved hull and phase shield.
        :return:
        """
        temp_player_list = [player1, player2, player3, player4, player5, player6,player7,player8,player9]
        player_list = []
        await interaction.response.defer(thinking=True)
        for i in temp_player_list:
            if i is not None:
                player_list.append([i.id, i.name])
        if not ai_ship_type:
            ai_ships = "def"
        else:
            ai_ships = ai_ship_type.value
        new_game = GameInit(game_name, player_list, ai_ships, rift_cannon, turn_order_variant, community_parts)
        new_game.create_game()

        async def get_or_create_category(guild: discord.Guild, category_name):
            """Get an existing category or create a new one."""
            for category in guild.categories:
                if category.name == category_name:
                    return category
            # If category doesn't exist, create it
            overwrites = {
                # Deny access to everyone else
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            }
            return await guild.create_category(category_name, overwrites=overwrites)

        async def get_or_create_role(guild: discord.Guild, role_name):
            for role in guild.roles:
                if role.name == role_name:
                    return role
            return await guild.create_role(name=role_name, mentionable=True)

        if config.game_number <= 10:
            category_name = "Games #1-10"
        else:
            start = 10 * ((config.game_number - 1) // 10) + 1
            end = start + 9
            category_name = f"Games #{start}-{end}"
        category = await get_or_create_category(interaction.guild, category_name)

        role_name = f"aeb{config.game_number}"
        role = await get_or_create_role(interaction.guild, role_name)
        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      role: discord.PermissionOverwrite(read_messages=True, manage_messages=True)}

        for player_id in player_list:
            member = interaction.guild.get_member(player_id[0])
            if member:
                await member.add_roles(role)
                overwrites[member] = discord.PermissionOverwrite(read_messages=True,
                                                                 manage_messages=True)  # Grant access to the player
        roleObv = discord.utils.get(interaction.guild.roles, name="Observers")
        if roleObv:
            overwrites[roleObv] = discord.PermissionOverwrite(read_messages=True)
        # Create the text channels for the game
        tabletalk = await interaction.guild.create_text_channel(f'aeb{config.game_number}-{game_name}',
                                                                category=category, overwrites=overwrites)
        actions = await interaction.guild.create_text_channel(f'aeb{config.game_number}-actions',
                                                              category=category, overwrites=overwrites)
        thread_name = f'aeb{config.game_number}-bot-map-updates'
        thread = await actions.create_thread(name=thread_name, auto_archive_duration=10080,type=discord.ChannelType.public_thread)
        new_game.update_num()
        game = GamestateHelper(actions)
        if player_count < 2:
            player_count = 2
        if player_count > 9:
            player_count = 9
        msgBig = ""
        if hyperlanes:
            if player_count != 4 and player_count != 5:
                hyperlanes = False
                msgBig += "## Hyperlanes cannot be enabled in anything except 4 or 5 player games at the moment, so they have not been enabled for this game"
            else:
                msgBig +="## Hyperlanes have been enabled for this game"
        if galactic_event_tiles:
            msgBig += "\n## Galactic Event Tiles have been added to this game"
        if rift_cannon:
            msgBig += "\n## Rift Cannons have been added to this game"
        if msgBig != "":
            await actions.send(msgBig)

        game.setup_techs_and_outer_rim(player_count, galactic_event_tiles, hyperlanes)
        drawing = DrawHelper(game.gamestate)


        minorSpeciesList = ""
        for species in game.gamestate["minor_species"]:
            minorSpeciesList += species + "\n"
        await thread.send(role.mention + " pinging you here")
        await actions.send("Initial tech draw is as follows", file=drawing.show_available_techs())
        await actions.send(f"{role.mention}, draft factions and turn position in the manner of your choice,"
                           + " then setup the game with /setup game. "
                           + "Enter the players in the order they should take turns in"
                           + " (i.e. enter first player first). "
                           + "A draft has been started for you that you may use instead of the slash command.")
        await actions.send("A common way to draft factions is to generate a random pick order"
                           + " and then have the turn order be the reverse of that pick order. "
                           + "For your convenience, the following random pick order was generated,"
                           + " but you may ignore it. \n" +
                           "This game has been set to auto include minor species,"
                           + " 4 of which have been drawn at random below. "
                           + "If you want to disable this, you may use `/game disable_minor_species`. "
                           + "The minor species are as follows:\n"
                           + minorSpeciesList,
                           file=drawing.show_minor_species())
        file = await asyncio.to_thread(drawing.show_AI_stats)
        await actions.send("AI stats look like this", file=file)
        await DraftButtons.startDraft(game, player_list, interaction, actions, ban_factions)

        factionThread = await actions.create_thread(name="Faction Reference", auto_archive_duration=10080)
        boardPrefix = "images/resources/components/factions/"

        message = "\n".join(["# Eridani Empire",
                             "- 2🛡 Draw two random Reputation Tiles before the game starts,"
                             + " and place them facedown on your Reputation Track.",
                             "- -2 🔴 Start with two fewer Influence Discs"
                             + " (leave your two leftmost Influence Track spaces empty).",
                             "- These Ship Blueprints have additional Energy Production:",
                             "  - **Interceptor** - 1⚡",
                             "  - **Cruiser** - 1⚡",
                             "  - **Dreadnought** - 1⚡"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "eridani_board.png"))

        message = "\n".join(["# Hydran Progress",
                             "- ⚗️ During game setup, place a Population Cube in the"
                             + " Advanced Science Population Square on your Starting Sector."])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "hydran_board.png"))

        message = "\n".join(["# Planta",
                             "- Your Population Cubes are automatically destroyed by"
                             + " opponent Ships at the end of the Combat Phase.",
                             "- 1 extra VP for each Controlled Sector at the end of the game.",
                             "- All Ship Blueprints have reduced Initiative Bonuses.",
                             "- All Ship Blueprints have additional Computers and Energy Production"
                             + " but have one less Ship Part Space:",
                             "  - **Interceptor**, **Cruiser**, **Dreadnought** - +1⬜ 2⚡",
                             "  - **Starbase** - +1⬜ 5⚡"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "planta_board.png"))

        message = "\n".join(["# Descendants of Draco",
                             "- __Explore Action__: For each Activation, you may flip"
                             + " two Sectors from which to choose one (or none)to place."
                             + " Unplaced Sectors are discarded faceup in the corresponding Sector Discard Pile.",
                             "- 1 VP per Ancient on the game board at the end of the game.",
                             "- You may have Ships in Sectors containing Ancients"
                             + " but are not allowed to battle the Ancients."
                             + " Your ships are not Pinned by Ancients."
                             + " You may place Influence Discs in Sectors with Ancients;"
                             + " you are not allowed to collect Discovery Tiles from Sectors containing Ancients."])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "draco_board.png"))

        message = "\n".join(["# Mechanema",
                             "- Cheaper Building costs (instead of):",
                             "  - **Interceptor**: 2🔧 (3)",
                             "  - **Cruiser**: 4🔧 (5)",
                             "  - **Dreadnought**: 7🔧 (8)",
                             "  - **Starbase**: 2🔧 (3)",
                             "  - **Orbital**: 3🔧 (4)",
                             "  - **Monolith**: 8🔧 (10)"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "mechanema_board.png"))

        message = "\n".join(["# Orion Hegemony",
                             "- Start with a Cruiser in your Starting Sector instead of an Interceptor.",
                             "- All Ship Blueprints have increased Initiative Bonuses.",
                             "- These Ship Blueprints have additional Energy Production:",
                             "  - **Interceptor**: 1⚡",
                             "  - **Cruiser**: 2⚡",
                             "  - **Dreadnought**: 3⚡"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "orion_board.png"))

        message = "\n".join(["# Wardens of Magellan",
                             "- Start with a Discovery Tile facedown on the Discovery Tile Symbol"
                             + " on the top Tech Track of your Species Board.",
                             "- Resolve the Discovery Tile on your Species Board the first time"
                             + " you place a fourth Tech on one of your Tech Tracks."
                             + " If the Discovery Tile allows you to place something in a Sector"
                             + " (such as Ancient Cruiser or Ancient Orbital), place it in your Starting Sector."
                             + " If you do not control your Starting Sector, you must take the tile as 2VP.",
                             "- 1 VP at the end of the game per Discovery Tile you used as a Ship Part.",
                             "- At any time, you may flip unused Colony Ships to gain"
                             + " one Resource of your choice per Colony Ship flipped."
                             + " (Note: only refresh 1 colony ship with the influence action)"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "magellan_board.png"))
        message = "\n".join(["# Enlightened of Lyra",
                             "- 1 VP per Shrine\\* you control at the end of the game.",
                             "- During the Combat Phase, you may flip unused Colony Ships"
                             + " to reroll one of your own dice per Colony Ship flipped.",
                             "## - \\*Shrines",
                             "- You start the game with nine Shrines (special Structures)"
                             + " on the indicated spaces of your Shrine Board])",
                             "- With each **Research** Action, you may additionally place "
                             + "one Shrine from your Shrine Board"
                             + " in any Sector you Control by paying its indicated cost"
                             + " and adhering to the following restrictions:",
                             "  - Shrines must be placed next to a planet of the same color"
                             + " as the Resource used to place the Shrine (or a gray planet).",
                             "  - Each planet may have only one Shrine.",
                             "- Shrines cannot be placed using the **Build** Action.",
                             "- When you place the last Shrine from a row of the Shrine Board,"
                             + " gain the indicated bonus:",
                             "  - __Wormhole Generator ability__: You may Explore, Move to, and Influence "
                             + "adjacent Sectors if the edges connecting the Sectors contain one Wormhole.",
                             "  - __Discovery Tile__: If the Discovery Tile allows you to place something in a Sector"
                             + " (such as Ancient Cruiser or Ancient Orbital), place it in your Starting Sector."
                             + " If you do not control your Starting Sector, you must take the tile as 2VP.",
                             "  - __Extra Influence Disc__: You receive one additional Influence Disc,"
                             + " placed immediately on your Influence Track"
                             + " (you start with 4 extra Influence Discs in your Species Tray instead of 3)."])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "lyra_board.png"))
        message = "\n".join(["# The Exiles",
                             "- Start with an Orbital in your Starting Sector.",
                             "- 1 VP for each Orbital with your Population Cube at the end of the game.",
                             "- Orbitals with your Population Cubes are considered Ships:",
                             "  - They have their own Blueprints but are unable to receive Drive Ship Part Tiles",
                             "  - When destroyed in battle, return your Population Cube to the"
                             + " Science or Money Graveyard, but do not remove the Orbital miniature.",
                             "  - our destroyed Orbitals each add 1 to your opponent’s Reputation Tile draw (max 5).",
                             "- You cannot construct Starbases.",
                             "- Your Orbitals have Ship Blueprints."])
        await factionThread.send(message, file=drawing.get_file("images/resources/components/factions/exile_board.png"))

        message = "\n".join(["# Rho Indi Syndicate",
                             "- Start with two Interceptors in your Starting Sector.",
                             "- You have only two Ambassador Tiles.",
                             "- After drawing Reputation Tiles, gain Money equal to"
                             + " the number of Reputation Tiles you drew minus 1.",
                             "- You do not lose VP for holding the Traitor Card at the end of the game.",
                             "- You cannot construct Dreadnoughts.",
                             "- Increased Building costs (instead of):",
                             "  - **Interceptor**: 4🔧 (3)",
                             "  - **Cruiser**: 6🔧 (5)",
                             "  - **Starbase**: 4🔧 (3)",
                             "- Interceptor and Cruiser Ship Blueprints have increased Initiative Bonuses.",
                             "- All Ship Blueprints have additional **Gauss Shields**:",
                             "  - **Interceptor**: -1⬛",
                             "  - **Cruiser**: -1⬛",
                             "  - **Dreadnought**: -1⬛"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "rho_board.png"))

        message = "\n".join(["# Terrans"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "terran_conglomerate_board.png"))

        message = "\n".join(["Rift Reference"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "Rift_Reference.png"))

        message = "\n".join(["Minor Species Reference"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "Minor_Species_Reference.png"))

        message = "\n".join(["Discovery Reference"])
        await factionThread.send(message, file=drawing.get_file(boardPrefix + "Discovery_Reference.png"))
        game.release_lock()
        await factionThread.send(role.mention + " pinging you here, which contains all the faction sheets")
        await interaction.followup.send("\n".join(["New game created! Here are the channels:",
                                                   tabletalk.jump_url, actions.jump_url]))
        if isinstance(interaction.channel, discord.Thread):
            new_name = f"[Launched] {interaction.channel.name}"
            await interaction.channel.edit(name=new_name)
            await interaction.channel.edit(archived=True)
