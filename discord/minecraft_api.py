import discord
import requests_cache
import os
from discord import app_commands
from retry_requests import retry
from dotenv import load_dotenv


load_dotenv()


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 300)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
base_url = os.getenv("API_BASE_URL")
headers = {
    "Authorization": os.getenv("API_TOKEN")
}

# discord
intents = discord.Intents.default()
client = discord.Client(intents = intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")


# get whitelist
@tree.command(name="get_whitelist", description="ホワイトリストに登録されているユーザーを取得する")
#@app_commands.guilds(922298705456005151)
async def get_whitelist(interaction: discord.Integration):
    response = retry_session.get(f"{base_url}/whitelist", headers=headers)

    if response.status_code == 200:
        data = response.json()
        await interaction.response.send_message(content=f"登録済みユーザー: {','.join(data['players'])}", ephemeral=True)
        return

    await interaction.response.send_message(content="APIの実行に失敗しました", ephemeral=True)


@tree.command(name="add_whitelist", description="指定のユーザーをホワイトリストに追加する")
@app_commands.describe(user="ユーザー名")
#@app_commands.guilds(922298705456005151)
async def add_whitelist(interaction: discord.Integration, user: str):
    response = retry_session.get(f"{base_url}/whitelist/{user}", headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data["whitelisted"]:
            await interaction.response.send_message(content=f"{user}はすでにホワイトリストに登録されています", ephemeral=True)
            return
        response = retry_session.post(f"{base_url}/whitelist/add/{user}", headers=headers)

        if response.status_code == 200:
            await interaction.response.send_message(content=f"{user}をホワイトリストに追加しました", ephemeral=True)
            return
        await interaction.response.send_message(content="API(POST)の実行に失敗しました", ephemeral=True)
    else:
        await interaction.response.send_message(content="API(GET)の実行に失敗しました", ephemeral=True)


if __name__ == "__main__":
    client.run(os.getenv('DISCORD_TOKEN'))
