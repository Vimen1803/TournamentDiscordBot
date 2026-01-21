import discord
from discord.ext import commands
import asyncio
from config import BOT, PREFIX, LOG_CHANNEL
from utils.db import DBManager
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

async def get_or_create_invite(guild):
    """
    Obtiene el enlace de invitación de la DB si existe y es válido.
    Si no existe o no es válido, crea uno nuevo y lo guarda en la DB.
    """
    config = await DBManager.get_guild_config(guild.id)
    
    # Verificar si ya existe un invite guardado
    if config and config.get('invite_url'):
        stored_invite = config.get('invite_url')
        
        # Verificar si el invite es válido
        try:
            invites = await guild.invites()
            for inv in invites:
                if inv.url == stored_invite:
                    # El invite existe y es válido
                    return stored_invite
        except:
            pass
    
    # El invite no existe o no es válido, crear uno nuevo
    invite_url = None
    try:
        # Buscar un canal válido para crear el invite
        target_ch = guild.system_channel or next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), 
            None
        )
        if target_ch:
            inv = await target_ch.create_invite(max_age=0, max_uses=0, reason="Bot startup invite")
            invite_url = inv.url
            
            # Guardar el invite en la DB
            await DBManager.update_guild_config_field(guild.id, 'invite_url', invite_url)
    except Exception as e:
        print(f"Could not create invite for {guild.name}: {e}")
    
    return invite_url

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    log_channel = bot.get_channel(LOG_CHANNEL)
    if log_channel:
        guilds_data = []
        for g in bot.guilds:
            invite_url = await get_or_create_invite(g)
            invite_display = invite_url if invite_url else "No disponible"
            guilds_data.append(f"• **{g.name}** (ID: {g.id})\n  Link: {invite_display}")
            
        guilds_info = "\n".join(guilds_data) or "Ninguno"
        
        embed = discord.Embed(title="Bot Iniciado", description=f"El bot **{bot.user.name}** está listo.", color=discord.Color.green())
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        embed.add_field(name=f"Servidores ({len(bot.guilds)})", value=guilds_info, inline=False)
        
        await log_channel.send(embed=embed)

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(BOT)

if __name__ == "__main__":
    asyncio.run(main())
