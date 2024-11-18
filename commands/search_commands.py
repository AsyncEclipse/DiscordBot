import discord
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper

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
                                        f"\n> Description: {tech_info['description']}",
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
                                        f"\n> Description: {tech_info['description']}",
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
                                        f"\n> Description: {part_info['description']}",
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
                                        f"\n> Description: {part_info['description']}",
                                        file=image)


  
