import json
import datetime
import discord
from discord.ext import commands
from discord import app_commands
import os
import scrap_darkino
import asyncio
import dotenv
from darkinolog import DarkinoLog


dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

darkino_log = DarkinoLog()

os.system("clear")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
old_all_movies = []
all_movies = []
guild_dict = {}





async def update_channels(guild):
    global guild_dict
    """
    Update alls channel in guild_dict
    :param guild: Guild object of Discord API
    :return:
    """
    guild_dict[str(guild.id)]["channels_id"] = [str(channel.id) for channel in await guild.fetch_channels()]


async def send_embed(channel: discord.TextChannel, title: str, descritpion: str, image_url: str, movie: dict, dl_url: str) -> None:
    embed = discord.Embed(title=title, description=descritpion)
    embed.set_image(url=image_url)

    film_info = scrap_darkino.__get_film_info__(movie)
    genders, actors, descritpion, trailer_link = film_info[2], film_info[1], film_info[0], film_info[3]
    embed.add_field(name="Genre(s)", value=genders, inline=False)
    embed.add_field(name="Acteur(s)", value=actors, inline=False)
    embed.add_field(name="Description", value=descritpion, inline=False)
    if trailer_link:
        embed.add_field(name="Bande annonce", value=f"[Bande annonce ici]({trailer_link})", inline=False)
    embed.add_field(name="Téléchargement", value=f"[Télécharger ici]({dl_url})", inline=False)
    embed.set_footer(text="by ezvizion")
    await channel.send(embed=embed)


async def print_new_film() -> None:
    global old_all_movies, all_movies
    """
    This function print the new film on the selected channel of all guilds where the bot is.
    Executed every hour
    :return: Nothing
    """
    if not old_all_movies:
        old_all_movies = retrieve_dict("all_movies.json")
    all_movies = scrap_darkino.get_all_latest()
    if not all_movies:
        return
    
    # New film has been uploaded

    if type(old_all_movies) is bool: # Debug
        print(old_all_movies)
    new_movies = []
    if len(old_all_movies) > 0:
        for movie in all_movies:
            if not any(movie["title"] == old_movie["title"] for old_movie in old_all_movies):
                new_movies.append(movie)
                
    for guild_id in guild_dict:
        if guild_dict[guild_id]["latest_film_channel_id"]:
            film_channel = bot.get_channel(int(guild_dict[guild_id]["latest_film_channel_id"]))
            for new_movie in new_movies:
                await send_embed(
                    channel=film_channel,
                    title=new_movie['title'],
                    descritpion=f"{new_movie['date_post']}.\n"
                                f"**Date de production** : {new_movie['year_prod']}",
                    image_url=new_movie["img_url"],
                    movie=new_movie,
                    dl_url=new_movie['redirect_url'])
                darkino_log.print_log(title="New film ", value=f"New film found : '{new_movie['title']}'", color="GREEN", save=True)
    old_all_movies = all_movies


async def loop_get_film() -> None:
    while True:
        await print_new_film()
        await asyncio.sleep(600)


def retrieve_dict(filename) -> dict | list:
    path = os.path.abspath(__file__)
    repo = os.path.dirname(path)
    verif_path = os.path.join(repo, filename)
    if not os.path.isfile(verif_path):
        darkino_log.print_log(title="Json extraction", value=f"No such file named '{filename}'", color="RED", save=True)
        return {}
    with open(filename, "r") as f:
        json_data = json.load(f)
    darkino_log.print_log(title="Json extraction", value=f"Successfully extracted '{filename}'", color="GREEN", save=True)
    return json_data


def save_dict(dict_to_save: dict, filename: str) -> None:
    if not dict_to_save:
        return
    with open(filename, "w") as f:
        json.dump(dict_to_save, f, indent=4)


# ----------------------------- EVENTS -----------------------------

@bot.event
async def on_ready():
    global guild_dict
    # guild_dict[guild_id]["..."]
    guild_dict = retrieve_dict("guild_dict.json")
    if not guild_dict:
        for guild in bot.guilds:
            guild_dict[str(guild.id)] = {
                "title": guild.name,
                "member_count": guild.member_count,
                "channels_id": [str(channel.id) for channel in await guild.fetch_channels()],
                "latest_film_channel_id": None
            }
    try:
        synced = await bot.tree.sync()
        darkino_log.print_log(title="Syncing", value=f"Synced {len(synced)} command(s)", color="YELLOW", save=True)
    except Exception as e:
        print(e)
    bot.loop.create_task(loop_get_film())


@bot.event
async def on_guild_channel_create(channel):
    await update_channels(channel.guild)


@bot.event
async def on_guild_channel_delete(channel):
    await update_channels(channel.guild)


# ----------------------------- COMMANDS -----------------------------

@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello world ")


@bot.tree.command(name="set", description="Select the channel with its ID to get up to date to the latest films")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel_id: str):
    if channel_id in guild_dict[str(interaction.guild.id)]["channels_id"]:
        await interaction.response.send_message(f"le channel {bot.get_channel(int(channel_id)).name} existe bien")
        guild_dict[str(interaction.guild.id)]["latest_film_channel_id"] = channel_id
    else:
        await interaction.response.send_message(f"le channel {channel_id} n'existe pas")


@bot.tree.command(name="change_link", description="Set the a new Darkino Link")
@app_commands.checks.has_permissions(administrator=True)
async def change_link(interaction: discord.Interaction, url: str) -> None:
    """_summary_

    Args:
        interaction (discord.Interaction): Input command
        url (str): New Darkino URL
    """
    if url[-1] != "/":
        url += "/"
    if url[0:8] != "https://":
        url = "https://" + url
    last_url = os.environ["URL_LAST_2023"] 
    os.environ["URL_LAST_2023"] = url
    darkino_log.print_log("New URL set", f"{interaction.user} set a new url, from {last_url} to {url}", "YELLOW", save=True)
    dotenv.set_key(dotenv_file, "URL_LAST_2023", os.environ["URL_LAST_2023"])
    await interaction.response.send_message(f"Vous avez changé l'URL par {url} (anciennement: {last_url})")
        
# ----------------------------- OTHERS -----------------------------

bot.run(DISCORD_TOKEN)
save_dict(guild_dict, "guild_dict.json")
darkino_log.print_log("Saving", "guild_dict.json successfully saved", "GREEN", save=True)
save_dict(all_movies, "all_movies.json")
darkino_log.print_log("Saving", "all_movies.json successfully saved", "GREEN", save=True)

