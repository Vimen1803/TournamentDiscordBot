import discord
from discord.ext import commands
import uuid
import datetime
import random
import io
from utils.db import DBManager, Tournament, Match
from utils.visual import generate_bracket_image
from config import PREFIX, BUG_CHANNEL 

try:
    from config import BOT_LINK, DOC_URL
except ImportError:
    BOT_LINK = None
    DOC_URL = None

class Tourney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        return True

    def get_embed(self, title, description, color=discord.Color.blue(), author=None):
        embed = discord.Embed(title=title, description=description, color=color)
        if author:
            embed.set_footer(text=f"Solicitado por {author.display_name}", icon_url=author.avatar.url if author.avatar else None)
        else:
            embed.set_footer(text=f"Solicitado por {self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed

    async def send_log(self, guild, tourney_id: str, title: str, description: str, color: discord.Color):
        # Envía un log al canal de tourney_logs si está habilitado
        config = await DBManager.get_guild_config(guild.id)
        if not config:
            return
        
        logs_enabled = config.get("tourney_logs_enabled", False)
        log_channel_id = config.get("tourney_log_channel_id")
        
        if not logs_enabled or not log_channel_id:
            return
        
        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return
        
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=f"Servidor: {guild.name} | Server ID: {guild.id} | Torneo ID: {tourney_id}")
        embed.timestamp = discord.utils.utcnow()
        
        try:
            await channel.send(embed=embed)
        except:
            pass  # Si no se puede mandar pasa
    
    async def is_admin(self, ctx):
        # Revisa que el user tenga permisos de administrador o que tenga un rol permitido
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Revisa la configuración del servidor
        config = await DBManager.get_guild_config(ctx.guild.id)
        if config and 'admin_roles' in config:
            allowed_roles = config.get('admin_roles', [])
            for role in ctx.author.roles:
                if str(role.id) in allowed_roles:
                    return True
        return False
    
    async def admin_check(self, ctx):
        if not await self.is_admin(ctx):
            await ctx.send(embed=self.get_embed("Error", "No tienes permisos para ejecutar este comando.", discord.Color.red(), author=ctx.author))
            return False
        return True

    async def channel_check(self, ctx):
        # Revisa si el comando se ejecuta en los canales permitidos
        config = await DBManager.get_guild_config(ctx.guild.id)
        if not config:
             # Si no hay configuración, permite el comando en cualquier canal
             return True
        
        lobby_channel = config.get('lobby_channel_id')
        bot_admin_channel = config.get('bot_admin_channel_id')
        
        allowed_channels = []
        if lobby_channel: allowed_channels.append(int(lobby_channel))
        if bot_admin_channel: allowed_channels.append(int(bot_admin_channel))

        if not allowed_channels:
            return True # No restricción si no está configurado
            
        if ctx.channel.id not in allowed_channels:
            return False
        return True

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.get_embed("Error de Argumentos", f"Faltan argumentos para ejecutar el comando.\nUso: `{PREFIX}{ctx.command.qualified_name} {ctx.command.signature}`", discord.Color.red(), author=ctx.author))
        elif isinstance(error, commands.BadArgument):
             await ctx.send(embed=self.get_embed("Error de Argumentos", f"Argumento inválido.\nUso: `{PREFIX}{ctx.command.qualified_name} {ctx.command.signature}`", discord.Color.red(), author=ctx.author))
        else:
            # Propaga otros errores o maneja ellos
            # mantener el comportamiento por defecto para otros
            import traceback
            traceback.print_exception(type(error), error, error.__traceback__)

    @commands.group(invoke_without_command=True)
    async def tourney(self, ctx):
        await ctx.send_help(ctx.command)

    @tourney.command(name="link")
    async def invite_link(self, ctx):
        if not BOT_LINK:
            await ctx.send(embed=self.get_embed("Invitación del Bot", "No se ha configurado el enlace de invitación del bot.", author=ctx.author))
            return
        await ctx.send(embed=self.get_embed("Invitación del Bot", f"[Haz click aquí para invitarme]({BOT_LINK})", author=ctx.author))

    @tourney.command(name="doc")
    async def doc_link(self, ctx):
        if not DOC_URL:
            await ctx.send(embed=self.get_embed("Documentación del Bot", "No se ha configurado la documentación del bot.", author=ctx.author))
            return
        await ctx.send(embed=self.get_embed("Documentación del Bot", f"[Haz click aquí para ver la documentación]({DOC_URL})", author=ctx.author))

    @tourney.command(name="help")
    async def tourney_help(self, ctx):
        # Implementación de paginador para ayuda
        if DOC_URL:
            embed_user = self.get_embed("Ayuda - Comandos de Usuario (Página 1/2)", f"[**Documentación Completa del Bot**]({DOC_URL})", author=ctx.author)
        else:
            embed_user = self.get_embed("Ayuda - Comandos de Usuario (Página 1/2)", "", author=ctx.author)
        embed_user.add_field(name=f"\n{PREFIX}tourney register <nombre_equipo> [@miembros...]", value="Registra un equipo en el torneo activo.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney invite <@usuario>", value="Invita a un usuario a tu equipo (solo líder).", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney info [id_torneo]", value="Muestra información del torneo activo, o de uno específico por ID (incluso finalizados).", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney teams [id_torneo]", value="Muestra los equipos registrados.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney team <id_equipo>", value="Muestra info detallada de un equipo.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney historial", value="Muestra torneos pasados.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney link", value="Enlace de invitación del bot.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney doc", value="Documentación del bot.", inline=False)
        embed_user.add_field(name=f"{PREFIX}tourney bug <descripción del bug>", value="Reporta un bug.", inline=False)

        embed_admin = self.get_embed("Ayuda - Comandos de Admin (Página 2/2)", "", author=ctx.author)
        embed_admin.add_field(name=f"{PREFIX}tourney create <args...>", value=f"Crea torneo. Uso: `Nombre | Desc | Fecha | Hora | MaxTeams | MinMiem | MaxMiem` (Adjuntar foto)", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney start [id_torneo]", value="Inicia el torneo, genera brackets y canales.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set category <id>", value="Configura Categoría del torneo.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set bracket <id_canal>", value="Configura Canal de Brackets.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set lobby <id_canal>", value="Configura Canal de Lobby.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set bot_admin <id_canal>", value="Configura Canal de Admin.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set logs [id_canal]", value="Toggle logs ON/OFF. Con ID establece canal y activa.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney set winner <@miembro>", value="Define el ganador mencionando a un integrante.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney settings", value="Ver configuración actual.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney roles [add/remove] <@rol>", value="Gestionar roles de admin.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney kick <id_torneo> <id_equipo>", value="Expulsar equipo del torneo.", inline=False)
        embed_admin.add_field(name=f"{PREFIX}tourney delete <id_torneo>", value="Elimina un torneo de la base de datos.", inline=False)
        
        pages = [embed_user, embed_admin]
        
        class HelpPaginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.current_page = 0
            
            @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = (self.current_page - 1) % len(pages)
                await interaction.response.edit_message(embed=pages[self.current_page])

            @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = (self.current_page + 1) % len(pages)
                await interaction.response.edit_message(embed=pages[self.current_page])

        await ctx.send(embed=embed_user, view=HelpPaginator())

    @tourney.command(name="create")
    async def create_tourney(self, ctx, *, args: str = ""):
        if not await self.admin_check(ctx): return

        # Formato: Nombre | Descripción | Fecha (YYYY-MM-DD) | Hora (HH:MM) | MaxEquipos | MinMiembros | MaxMiembros
        # Foto via attachment (opcional)
        
        parts = [p.strip() for p in args.split('|')]
        if len(parts) < 7:
            await ctx.send(embed=self.get_embed("Error", f"Uso incorrecto. Formato:\n`{PREFIX}tourney create Nombre | Descripción | Fecha (YYYY-MM-DD) | Hora (HH:MM) | MaxEquipos | MinMiembros | MaxMiembros`\n\nAdjunta una imagen para el banner (opcional).", discord.Color.red(), author=ctx.author))
            return

        name = parts[0]
        desc = parts[1]
        date_str = parts[2]
        time_str = parts[3]
        
        try:
            max_teams = int(parts[4])
            min_members = int(parts[5])
            max_members = int(parts[6])
        except ValueError:
            await ctx.send(embed=self.get_embed("Error", "Los valores de MaxEquipos, MinMiembros y MaxMiembros deben ser números enteros.", discord.Color.red(), author=ctx.author))
            return

        if max_teams % 2 != 0:
            await ctx.send(embed=self.get_embed("Error", "El número máximo de equipos debe ser múltiplo de 2.", discord.Color.red(), author=ctx.author))
            return
        
        if max_teams > 64 or max_teams < 2:
            await ctx.send(embed=self.get_embed("Error", "El número máximo de equipos es 64 y el mínimo es 2.", discord.Color.red(), author=ctx.author))
            return

        # Imagen
        image_url = None
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif ctx.guild.icon:
            image_url = ctx.guild.icon.url

        # Revisa si ya hay un torneo activo
        if await DBManager.get_active_tournament(ctx.guild.id):
             await ctx.send(embed=self.get_embed("Error", "Ya hay un torneo activo. Finaliza primero.", discord.Color.red(), author=ctx.author))
             return

        full_start_date = f"{date_str} {time_str}"

        new_tourney = Tournament(
            id=str(uuid.uuid4())[:8],
            name=name,
            guild_id=ctx.guild.id,
            settings={},
            status="open",
            current_round=0,
            matches=[],
            created_at=datetime.datetime.utcnow(),
            description=desc,
            start_date=full_start_date,
            max_teams=max_teams,
            min_members=min_members,
            max_members=max_members,
            image_url=image_url
        )
        
        await DBManager.create_tournament(new_tourney.to_dict())
        
        # Log de creación de torneo
        await self.send_log(
            ctx.guild, new_tourney.id,
            "🏆 Torneo Creado",
            f"**{name}**\n{desc}\n\n**Fecha:** {full_start_date}\n**Equipos máx:** {max_teams}\n**Miembros:** {min_members}-{max_members}\n**Creado por:** {ctx.author.mention}",
            discord.Color.green()
        )
        
        embed = self.get_embed("Torneo Creado", f"**{name}**\n{desc}", author=ctx.author)
        embed.add_field(name="ID", value=new_tourney.id)
        embed.add_field(name="Inicio", value=full_start_date)
        embed.add_field(name="Límites", value=f"Equipos: {max_teams}\nMiembros: {min_members}-{max_members}")
        if image_url: embed.set_image(url=image_url)
        embed.set_footer(text="Configuración de servidor usada para canales/roles.")
        
        await ctx.send(embed=embed)

    @tourney.command(name="delete")
    async def delete_tourney(self, ctx, tourney_id: str):
        # Elimina un torneo de la base de datos (solo administradores)
        if not await self.admin_check(ctx): return
        
        # Verificar que el torneo existe
        tourney = await DBManager.get_tournament(tourney_id)
        if not tourney:
            await ctx.send(embed=self.get_embed("Error", f"No se encontró un torneo con ID `{tourney_id}`.", discord.Color.red(), author=ctx.author))
            return
        
        # Verificar que el torneo pertenece a este servidor
        if tourney['guild_id'] != ctx.guild.id:
            await ctx.send(embed=self.get_embed("Error", "Este torneo no pertenece a este servidor.", discord.Color.red(), author=ctx.author))
            return
        
        tourney_name = tourney.get('name', 'Sin nombre')
        tourney_status = tourney.get('status', 'unknown')
        
        # Eliminar equipos asociados
        await DBManager.delete_teams_by_tournament(tourney_id)
        
        # Eliminar el torneo
        await DBManager.delete_tournament(tourney_id)
        
        # Log de eliminación de torneo
        await self.send_log(
            ctx.guild, tourney_id,
            "🗑️ Torneo Eliminado",
            f"**{tourney_name}**\n\n**Estado anterior:** {tourney_status}\n**Eliminado por:** {ctx.author.mention}",
            discord.Color.orange()
        )
        
        embed = self.get_embed(
            "Torneo Eliminado",
            f"El torneo **{tourney_name}** (ID: `{tourney_id}`) ha sido eliminado correctamente.",
            discord.Color.orange(),
            author=ctx.author
        )
        embed.add_field(name="Estado anterior", value=tourney_status, inline=True)
        embed.add_field(name="Eliminado por", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)

    @tourney.command(name="settings")
    async def show_settings(self, ctx):
        if not await self.admin_check(ctx): return
        
        config = await DBManager.get_guild_config(ctx.guild.id)
        if not config:
             await ctx.send(embed=self.get_embed("Error", "No hay configuración de servidor guardada.", discord.Color.red(), author=ctx.author))
             return
             
        roles = config.get("admin_roles", [])
        roles_str = ", ".join([f"<@&{r}>" for r in roles]) or "Ninguno"
        logs_state = "ON" if config.get("tourney_logs_enabled", False) else "OFF"
        
        desc = f"**Categoría:** {config.get('category_id')}\n" \
               f"**Bracket Channel:** <#{config.get('bracket_channel_id')}>\n" \
               f"**Lobby Channel:** <#{config.get('lobby_channel_id')}>\n" \
               f"**Bot Admin Channel:** <#{config.get('bot_admin_channel_id')}>\n" \
               f"**Logs Channel:** <#{config.get('tourney_log_channel_id')}> ({logs_state})\n" \
               f"**Roles Admin:** {roles_str}"
               
        await ctx.send(embed=self.get_embed(f"Configuración del Servidor", desc, author=ctx.author))



    # Control de Torneo 

    @tourney.command(name="start")
    async def start_tourney(self, ctx, tourney_id: str = None):
        if not await self.admin_check(ctx): return
        
        if tourney_id:
            tourney = await DBManager.get_tournament(tourney_id)
        else:
            tourney = await DBManager.get_active_tournament(ctx.guild.id)
            
        if not tourney:
             await ctx.send(embed=self.get_embed("Error", "Torneo no encontrado.", discord.Color.red(), author=ctx.author))
             return
             
        if tourney['status'] != "open":
             await ctx.send(embed=self.get_embed("Error", "El torneo ya está activo o finalizado.", discord.Color.red(), author=ctx.author))
             return
             
        teams = await DBManager.get_teams(tourney['id'])
        if len(teams) < 2:
             await ctx.send(embed=self.get_embed("Error", "Se necesitan al menos 2 equipos para iniciar.", discord.Color.red(), author=ctx.author))
             return

        # Logica de inicio
        # 1. Actualizar estado
        # 2. Generar primeras rondas con capacidad fija (max_teams)
        
        capacity = tourney.get('max_teams', 16)
        num_matches = capacity // 2
        matches = [None] * num_matches
        
        # Calcular capacidad (Potencia de 2 más cercana)
        # Estrategia de distribución alternada
        # Partidos: 0..num_matches-1
        # Dividir en índices izquierda y derecha
        half = num_matches // 2
        left_indices = list(range(0, half))
        right_indices = list(range(half, num_matches))
        
        # Interleave indices: L0, R0, L1, R1...
        fill_order = []
        for l, r in zip(left_indices, right_indices):
            fill_order.append(l)
            fill_order.append(r)
        
        # If odd number of matches (unlikely with power of 2, but robust check)
        if len(right_indices) > len(left_indices):
            fill_order.append(right_indices[-1])
            
        shuffled_teams = list(teams) # Copy
        random.shuffle(shuffled_teams)
        
        # Inicializar partidos
        for i in range(num_matches):
            matches[i] = {"team1_id": None, "team2_id": None, "winner_id": None, "channel_id": None}
            
        # Paso 1: Rellenar Slot 1
        for idx in fill_order:
            if not shuffled_teams: break
            matches[idx]['team1_id'] = shuffled_teams.pop(0)['id']
            
        # Paso 2: Rellenar Slot 2
        for idx in fill_order:
            if not shuffled_teams: break
            matches[idx]['team2_id'] = shuffled_teams.pop(0)['id']
            
        # Limpieza / Resolución automática de BYEs
        for i in range(num_matches):
            m = matches[i]
            # Si Slot 1 está vacío, significa que Slot 2 también lo está (orden de pop)
            if not m['team1_id']:
                 m['winner_id'] = "BYE_SLOT"
            elif not m['team2_id']:
                 # Team vs BYE
                 m['winner_id'] = m['team1_id']
            else:
                 # Team vs Team
                 m['winner_id'] = None

        # Actualizar DB
        tourney['status'] = "active"
        tourney['current_round'] = 1
        tourney['matches'] = [matches]
        
        await DBManager.update_tournament(tourney['id'], {
            "status": "active",
            "current_round": 1,
            "matches": tourney['matches']
        })
        
        # Log de inicio de torneo
        teams_names = [t['name'] for t in teams]
        await self.send_log(
            ctx.guild, tourney['id'],
            "🚀 Torneo Iniciado",
            f"**{tourney['name']}**\n\n**Equipos:** {len(teams)} / {capacity}\n**Partidos R1:** {num_matches}\n**Equipos participantes:**\n" + "\n".join([f"• {n}" for n in teams_names]),
            discord.Color.green()
        )
        
        await ctx.send(f"Iniciando torneo **{tourney['name']}** con {len(teams)} equipos (Capacidad: {capacity} - {num_matches} Partidos)!")
        
        # Procesar ronda (Crear canales + Bracket)
        await self.process_round(ctx, tourney)
        
        # Verificar avance automático (Round 1 completamente decidida)
        if all(m['winner_id'] for m in matches):
             await ctx.send("¡Primera ronda resuelta automáticamente (BYEs)! Avanzando...")
             await self.advance_round(ctx, tourney)

    def create_match_dict(self, t1, t2):
        # Reemplazado por la lógica inline arriba.
        pass

    async def process_round(self, ctx, tourney):
        guild = ctx.guild
        round_num = tourney['current_round']
        current_round_matches = tourney['matches'][round_num - 1]
        
        # Configuración global
        config = await DBManager.get_guild_config(guild.id)
        if not config: config = {}
        
        # Actualizar Bracket Image
        teams_data = await DBManager.get_teams(tourney['id'])
        team_names = {t['id']: t['name'] for t in teams_data}
        
        # Helper para descargar imagen
        async def fetch_image(url):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.read()
            except:
                pass
            return None

        server_icon_bytes = None
        if guild.icon:
            server_icon_bytes = await fetch_image(guild.icon.url)
            
        tourney_image_bytes = None
        if tourney.get('image'):
             tourney_image_bytes = await fetch_image(tourney['image'])
        
        # Pasar nuevos assets al generador
        bracket_buf = generate_bracket_image(
            tourney, 
            round_num, 
            team_names,
            server_name=guild.name,
            server_icon_bytes=server_icon_bytes,
            tourney_image_bytes=tourney_image_bytes
        )
        
        bracket_channel_id = config.get('bracket_channel_id')
        if bracket_channel_id:
            ch = guild.get_channel(bracket_channel_id)
            if ch:
                file = discord.File(bracket_buf, filename="bracket.png")
                await ch.send(content=f"Ronda {round_num}", file=file)

        # Crear canales
        category_id = config.get('category_id')
        category = guild.get_channel(category_id) if category_id else None
        
        if not category:
             pass

        new_matches_state = []
        
        for match in current_round_matches:
            # Saltear si ya se decidió (BYE)
            if match['winner_id']:
                new_matches_state.append(match)
                continue
            
            # Filtrar BYE_SLOT de las consultas a la DB
            t1_id = match['team1_id']
            t2_id = match['team2_id']
            if t1_id == "BYE_SLOT": t1_id = None
            if t2_id == "BYE_SLOT": t2_id = None
            
            t1 = next((t for t in teams_data if t['id'] == t1_id), None)
            t2 = next((t for t in teams_data if t['id'] == t2_id), None)
            
            if t1 and t2 and category:
                # Permission Overwrites
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True)
                }
                
                # Agregar permisos de miembros
                match_members = t1['members'] + t2['members']
                for uid in match_members:
                    member = guild.get_member(uid)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                ch_name = f"{t1['name']}-vs-{t2['name']}"
                try:
                    channel = await guild.create_text_channel(ch_name, category=category, overwrites=overwrites)
                    match['channel_id'] = channel.id
                    
                    # Enviar embed de info
                    embed = self.get_embed("Enfrentamiento", f"**{t1['name']}** vs **{t2['name']}**", author=ctx.author)
                    embed.add_field(name=t1['name'], value="\n".join([f"<@{m}>" for m in t1['members']]))
                    embed.add_field(name=t2['name'], value="\n".join([f"<@{m}>" for m in t2['members']]))
                    await channel.send(embed=embed)
                    await channel.send(f"<@{t1['leader_id']}> <@{t2['leader_id']}> ¡Comenzad!")
                    
                except Exception as e:
                    print(f"Error creating channel: {e}")
            
            new_matches_state.append(match)
            
        # Actualizar match channel IDs en DB
        tourney['matches'][round_num - 1] = new_matches_state
        await DBManager.update_tournament(tourney['id'], {"matches": tourney['matches']})

    @tourney.group(name="set", invoke_without_command=True)
    async def tourney_set(self, ctx):
         await ctx.send_help(ctx.command)

    async def update_setting_helper(self, ctx, key, value):
        if not await self.admin_check(ctx): return

        try:
            val_int = int(str(value).replace("<#", "").replace(">", ""))
            await DBManager.update_guild_config_field(ctx.guild.id, key, val_int)
            await ctx.send(embed=self.get_embed("Configuración Actualizada", f"**{key}** actualizado a `{val_int}` (<#{val_int}>)", author=ctx.author))
        except ValueError:
            await ctx.send(embed=self.get_embed("Error", "Valor inválido. Debe ser un ID o mención de canal.", discord.Color.red(), author=ctx.author))

    @tourney_set.command(name="category")
    async def set_category(self, ctx, category_id: str):
        await self.update_setting_helper(ctx, "category_id", category_id)

    @tourney_set.command(name="bracket")
    async def set_bracket(self, ctx, channel_id: str):
        await self.update_setting_helper(ctx, "bracket_channel_id", channel_id)

    @tourney_set.command(name="lobby")
    async def set_lobby(self, ctx, channel_id: str):
        await self.update_setting_helper(ctx, "lobby_channel_id", channel_id)

    @tourney_set.command(name="bot_admin")
    async def set_bot_admin(self, ctx, channel_id: str):
        await self.update_setting_helper(ctx, "bot_admin_channel_id", channel_id)

    @tourney_set.command(name="logs")
    async def set_logs(self, ctx, channel_id: str = None):
        # Configura el canal de logs del torneo. Sin ID actúa como toggle ON/OFF.
        if not await self.admin_check(ctx): return
        
        config = await DBManager.get_or_create_guild_config(ctx.guild.id)
        logs_enabled = config.get("tourney_logs_enabled", False)
        
        if channel_id:
            # Con ID: establecer canal y activar
            try:
                val_int = int(str(channel_id).replace("<#", "").replace(">", ""))
                await DBManager.update_guild_config_field(ctx.guild.id, "tourney_log_channel_id", val_int)
                await DBManager.update_guild_config_field(ctx.guild.id, "tourney_logs_enabled", True)
                await ctx.send(embed=self.get_embed("Logs Activados", f"Canal de logs establecido a <#{val_int}>.\nEstado: **ON**", author=ctx.author))
            except ValueError:
                await ctx.send(embed=self.get_embed("Error", "ID de canal inválido.", discord.Color.red(), author=ctx.author))
        else:
            # Sin ID: toggle
            new_state = not logs_enabled
            await DBManager.update_guild_config_field(ctx.guild.id, "tourney_logs_enabled", new_state)
            state_str = "ON" if new_state else "OFF"
            await ctx.send(embed=self.get_embed("Logs Toggle", f"Logs de torneo: **{state_str}**", author=ctx.author))

    @tourney_set.command(name="winner")
    async def set_winner_cmd(self, ctx, member: discord.Member):
        if not await self.admin_check(ctx): return
        
        tourney = await DBManager.get_active_tournament(ctx.guild.id)
        if not tourney or tourney['status'] != "active":
             await ctx.send(embed=self.get_embed("Error", "No hay torneo activo.", discord.Color.red(), author=ctx.author))
             return
             
        # Buscar equipo para este miembro
        team_id = None
        user_team = await DBManager.get_team_by_member(member.id, tourney['id'])
        if user_team:
            team_id = user_team['id']
        else:
            await ctx.send(embed=self.get_embed("Error", f"El usuario {member.mention} no pertenece a ningún equipo en este torneo.", discord.Color.red(), author=ctx.author))
            return

        round_idx = tourney['current_round'] - 1
        current_matches = tourney['matches'][round_idx]
        
        found_match = None
        for match in current_matches:
            if match['team1_id'] == team_id or match['team2_id'] == team_id:
                found_match = match
                break
                
        if not found_match:
             await ctx.send(embed=self.get_embed("Error", "Equipo no encontrado en la ronda actual.", discord.Color.red(), author=ctx.author))
             return
             
        if found_match['winner_id']:
             await ctx.send(embed=self.get_embed("Error", "Este enfrentamiento ya tiene ganador.", discord.Color.red(), author=ctx.author))
             return
             
        # Establecer ganador
        found_match['winner_id'] = team_id
        
        # Cerrar canal?
        if found_match['channel_id']:
            ch = ctx.guild.get_channel(found_match['channel_id'])
            if ch:
                await ch.send(embed=self.get_embed("Ganador Establecido", f"El equipo **{user_team['name']}** avanza. (ID: {team_id})", author=ctx.author))
                pass 

        await DBManager.update_tournament(tourney['id'], {"matches": tourney['matches']})
        await ctx.send(embed=self.get_embed("Ganador Establecido", f"El equipo **{user_team['name']}** avanza.", author=ctx.author))
        
        # Verificar si la ronda está completa
        if all(m['winner_id'] for m in current_matches):
            await self.advance_round(ctx, tourney)

    async def advance_round(self, ctx, tourney):
        current_matches = tourney['matches'][tourney['current_round'] - 1]
        winners = [m['winner_id'] for m in current_matches]
        
        if len(winners) == 1:
            # FINAL
            winner_team = await DBManager.get_team(winners[0])
            
            # Manejar torneo vacío NO DEBERIA PASAR PERO BUENO POR SI ACASO
            if winners[0] == "BYE_SLOT":
                 await ctx.send(embed=self.get_embed("Torneo Finalizado", "El torneo ha finalizado sin ganador real (Rama vacía).", author=ctx.author))
                 tourney['status'] = "finished"
                 await DBManager.update_tournament(tourney['id'], {"status": "finished"})
                 return 

            server_name = ctx.guild.name
            
            # Enviar al canal de brackets en lugar del contexto actual
            config = await DBManager.get_guild_config(ctx.guild.id)
            bracket_channel_id = config.get('bracket_channel_id') if config else None
            
            target_channel = ctx.channel
            if bracket_channel_id:
                bc = ctx.guild.get_channel(bracket_channel_id)
                if bc: target_channel = bc

            # Generar bracket final
            teams_data = await DBManager.get_teams(tourney['id'])
            team_names = {t['id']: t['name'] for t in teams_data}
            
            # Helper para descargar imagen
            async def fetch_image(url):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                return await resp.read()
                except:
                    pass
                return None

            server_icon_bytes = None
            if ctx.guild.icon:
                server_icon_bytes = await fetch_image(ctx.guild.icon.url)
                
            tourney_image_bytes = None
            if tourney.get('image'):
                 tourney_image_bytes = await fetch_image(tourney['image'])
            
            # Asignar el ganador ANTES de generar el bracket para que aparezca en amarillo
            tourney['winner_id'] = winner_team['id']
            
            # Generar bracket final (Round count doesn't increase, just redraw with current state which has final winner)
            final_bracket_buf = generate_bracket_image(
                tourney, 
                tourney['current_round'], 
                team_names,
                server_name=ctx.guild.name,
                server_icon_bytes=server_icon_bytes,
                tourney_image_bytes=tourney_image_bytes
            )
            
            if final_bracket_buf:
                file = discord.File(final_bracket_buf, filename="final_bracket.png")
                await target_channel.send(content=f"", file=file)

            # Borrar canales de partidos
            if 'matches' in tourney:
                for round_matches in tourney['matches']:
                    for m in round_matches:
                        if m.get('channel_id'):
                            try:
                                channel = ctx.guild.get_channel(m['channel_id'])
                                if channel:
                                    await channel.delete(reason="Torneo finalizado")
                            except Exception as e:
                                print(f"Error deleting channel {m['channel_id']}: {e}")
            
            tourney['status'] = "finished"
            tourney['winner_id'] = winner_team['id']
            await DBManager.update_tournament(tourney['id'], {"status": "finished", "winner_id": winner_team['id']})

            # EMBED DE TORNEO FINALIZADO
            embed = discord.Embed(
                title="¡TORNEO FINALIZADO!",
                description=f"**{tourney.get('name', 'Torneo')}**\n\n{tourney.get('description', '')}",
                color=discord.Color.gold()
            )
            
            # Imagen del torneo como thumbnail (arriba a la derecha)
            thumbnail_url = tourney.get('image_url')
            if not thumbnail_url and ctx.guild.icon:
                thumbnail_url = ctx.guild.icon.url
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            
            # Información del torneo
            embed.add_field(name="Fecha", value=tourney.get('start_date', 'N/A'), inline=True)
            embed.add_field(name="Equipos", value=str(len(teams_data)), inline=True)
            embed.add_field(name="Rondas", value=str(tourney.get('current_round', 1)), inline=True)
            
            # Información del equipo ganador
            embed.add_field(name="EQUIPO CAMPEÓN", value=f"**{winner_team['name']}**", inline=False)
            
            # Miembros del equipo ganador
            members_mentions = [f"<@{uid}>" for uid in winner_team.get('members', [])]
            leader_id = winner_team.get('leader_id')
            members_str = "\n".join(members_mentions) if members_mentions else "Sin miembros"
            embed.add_field(name="LÍDER", value=f"<@{leader_id}>" if leader_id else "N/A", inline=True)
            embed.add_field(name="MIEMBROS", value=members_str, inline=True)
            
            # Footer con servidor
            embed.set_footer(
                text=f"Servidor: {ctx.guild.name}",
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None
            )
            
            # Log de fin de torneo
            await self.send_log(
                ctx.guild, tourney['id'],
                "🏆 Torneo Finalizado",
                f"**{tourney['name']}**\n\n**Campeón:** {winner_team['name']}\n**Líder:** <@{leader_id}>\n**Rondas jugadas:** {tourney.get('current_round', 1)}\n**Total equipos:** {len(teams_data)}",
                discord.Color.green()
            )
            
            await target_channel.send(embed=embed)
            
        else:
            # Siguiente ronda
            tourney['current_round'] += 1
            matches = []
            matches = []
            for i in range(0, len(winners), 2):
                if i + 1 < len(winners):
                     w1 = winners[i]
                     w2 = winners[i+1]
                     
                     new_match = {"team1_id": w1, "team2_id": w2, "winner_id": None, "channel_id": None}
                     
                     if w1 == "BYE_SLOT" and w2 == "BYE_SLOT":
                         new_match["winner_id"] = "BYE_SLOT"
                     elif w1 != "BYE_SLOT" and w2 == "BYE_SLOT":
                         new_match["winner_id"] = w1
                     elif w1 == "BYE_SLOT" and w2 != "BYE_SLOT":
                         new_match["winner_id"] = w2
                         
                     matches.append(new_match)
                else:
                     pass
            
            tourney['matches'].append(matches)
            await DBManager.update_tournament(tourney['id'], {
                "current_round": tourney['current_round'],
                "matches": tourney['matches']
            })
            
            # Log de resumen de ronda finalizada
            prev_round = tourney['current_round'] - 1
            prev_matches = tourney['matches'][prev_round - 1]
            team_names = await DBManager.get_teams(tourney['id'])
            team_map = {t['id']: t['name'] for t in team_names}
            
            summary_lines = []
            for m in prev_matches:
                t1_name = team_map.get(m['team1_id'], 'BYE') if m['team1_id'] != "BYE_SLOT" else "BYE"
                t2_name = team_map.get(m['team2_id'], 'BYE') if m['team2_id'] != "BYE_SLOT" else "BYE"
                winner_name = team_map.get(m['winner_id'], 'BYE') if m['winner_id'] != "BYE_SLOT" else "BYE"
                summary_lines.append(f"**{t1_name}** vs **{t2_name}** → 🏆 {winner_name}")
            
            await self.send_log(
                ctx.guild, tourney['id'],
                f"📊 Resumen Ronda {prev_round}",
                f"**{tourney['name']}**\n\n" + "\n".join(summary_lines) + f"\n\n*Avanzando a Ronda {tourney['current_round']}...*",
                discord.Color.purple()
            )
            
            await ctx.send(f"¡Ronda {tourney['current_round'] - 1} finalizada! Iniciando Ronda {tourney['current_round']}...")
            await self.process_round(ctx, tourney)

            # Revisa si la ronda esta completa
            new_round_matches = tourney['matches'][-1]
            if all(m['winner_id'] for m in new_round_matches):
                await ctx.send(f"¡Ronda {tourney['current_round']} resuelta automáticamente! Avanzando...")
                # Recursive call
                await self.advance_round(ctx, tourney)


    @tourney.group(name="roles")
    async def roles_group(self, ctx):
         if ctx.invoked_subcommand is None:
             await self.show_roles(ctx)

    async def show_roles(self, ctx):
        if not await self.admin_check(ctx): return
        
        config = await DBManager.get_guild_config(ctx.guild.id)
        if not config:
            await ctx.send("No hay configuración.")
            return

        roles = config.get("admin_roles", [])
        roles_mentions = [f"<@&{r}>" for r in roles]
        await ctx.send(embed=self.get_embed("Roles Permitidos", "\n".join(roles_mentions) if roles_mentions else "Ninguno", author=ctx.author))

    @roles_group.command(name="add")
    async def add_role(self, ctx, role: discord.Role):
        # Revisa que el usar tenga admin
        if not await self.admin_check(ctx): return
        
        config = await DBManager.get_or_create_guild_config(ctx.guild.id)
        current_roles = config.get("admin_roles", [])
        
        if str(role.id) not in current_roles:
            current_roles.append(str(role.id))
            await DBManager.update_guild_config_field(ctx.guild.id, "admin_roles", current_roles)
            await ctx.send(embed=self.get_embed("Rol Añadido", f"Se ha añadido {role.mention} a los permitidos.", author=ctx.author))
        else:
            await ctx.send(embed=self.get_embed("Error", "Ese rol ya está en la lista.", author=ctx.author))

    @roles_group.command(name="remove")
    async def remove_role(self, ctx, role: discord.Role):
        if not await self.admin_check(ctx): return
        
        config = await DBManager.get_or_create_guild_config(ctx.guild.id)
        current_roles = config.get("admin_roles", [])
        
        if str(role.id) in current_roles:
            current_roles.remove(str(role.id))
            await DBManager.update_guild_config_field(ctx.guild.id, "admin_roles", current_roles)
            await ctx.send(embed=self.get_embed("Rol Eliminado", f"Se ha eliminado {role.mention} de los permitidos.", author=ctx.author))
        else:
            await ctx.send(embed=self.get_embed("Error", "Ese rol no estaba en la lista.", author=ctx.author))

    @tourney.command(name="info")
    async def tourney_info(self, ctx, tourney_id: str = None):
        if not await self.channel_check(ctx): return

        if tourney_id:
            tourney = await DBManager.get_tournament(tourney_id)
        else:
            tourney = await DBManager.get_active_tournament(ctx.guild.id)
            
        if not tourney:
            await ctx.send(embed=self.get_embed("Error", "No se encontró torneo.", author=ctx.author, color=discord.Color.red()))
            return

        embed = self.get_embed(f"Info Torneo: {tourney['name']}", tourney.get('description', ''), author=ctx.author)
        embed.add_field(name="ID", value=tourney['id'], inline=True)
        embed.add_field(name="Estado", value=tourney['status'], inline=True)
        embed.add_field(name="Ronda Actual", value=str(tourney.get('current_round', 0)), inline=True)
        
        embed.add_field(name="Inicio Programado", value=tourney.get('start_date', 'N/A'), inline=False)
        
        teams = await DBManager.get_teams(tourney['id'])
        max_teams = tourney.get('max_teams', 'âˆž')
        embed.add_field(name="Equipos", value=f"{len(teams)} / {max_teams}", inline=True)
        
        min_m = tourney.get('min_members', 1)
        max_m = tourney.get('max_members', 5)
        embed.add_field(name="Miembros por Equipo", value=f"{min_m} - {max_m}", inline=True)
        
        if tourney.get("image_url"):
            embed.set_image(url=tourney["image_url"])
            
        await ctx.send(embed=embed)
        
    @tourney.command(name="historial")
    async def tourney_history(self, ctx):
        if not await self.channel_check(ctx): return
        
        # Helper para obtener la pagina
        async def get_history_page(page_num):
             # DB skip/limit
             items_per_page = 1
             skip = page_num * items_per_page
             history = await DBManager.get_tournaments_history(ctx.guild.id, skip=skip, limit=items_per_page)
             total = await DBManager.count_tournaments(ctx.guild.id)
             return history, total, items_per_page
             
        data, total, per_page = await get_history_page(0)
        if not data:
            await ctx.send("No hay historial.")
            return

        if not data:
            await ctx.send("No hay historial.")
            return

        # Helper para construir el embed
        async def build_history_embed(t, page, total):
            desc = t.get('description', '')
            embed = self.get_embed(f"Historial {page}/{total}: {t['name']}", desc, author=ctx.author)
            
            embed.add_field(name="ID", value=t['id'], inline=True)
            embed.add_field(name="Estado", value=t['status'], inline=True)
            embed.add_field(name="Fecha Inicio", value=t.get('start_date', 'N/A'), inline=True)
            
            if t.get('winner_id'):
                winner_team = await DBManager.get_team(t['winner_id'])
                w_name = winner_team['name'] if winner_team else "Desconocido"
                
                members_str = ""
                if winner_team:
                    members_str = " - ".join([f"<@{uid}>" for uid in winner_team['members']])
                
                embed.add_field(name="Ganador", value=f"**{w_name}** - {members_str}", inline=False)
            
            teams_count = await DBManager.get_teams(t['id'])
            embed.add_field(name="Equipos", value=str(len(teams_count)), inline=True)
            
            if t.get('image_url'): embed.set_image(url=t['image_url'])
            return embed

        embed = await build_history_embed(data[0], 1, total)

        # Paginator
        class HistoryPaginator(discord.ui.View):
            def __init__(self, cog, total_pages):
                super().__init__(timeout=60)
                self.cog = cog
                self.current_page = 0
                self.total_pages = total_pages

            async def update_embed(self, interaction):
                data, _, _ = await get_history_page(self.current_page)
                if not data: return
                t = data[0]
                embed = await build_history_embed(t, self.current_page + 1, self.total_pages)
                await interaction.response.edit_message(embed=embed)

            @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = (self.current_page - 1) % self.total_pages
                await self.update_embed(interaction)

            @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = (self.current_page + 1) % self.total_pages
                await self.update_embed(interaction)
                
        await ctx.send(embed=embed, view=HistoryPaginator(self, total))

    # Team Management

    @tourney.command(name="register")
    async def register_team(self, ctx, name: str, *members: discord.Member):
        active_tourney = await DBManager.get_active_tournament(ctx.guild.id)
        if not active_tourney:
             await ctx.send(embed=self.get_embed("Error", "No hay ningún torneo activo en este servidor para registrarse.", discord.Color.red(), author=ctx.author))
             return
        
        tourney_id = active_tourney['id']

        if name.startswith("<@") and name.endswith(">"):
             await ctx.send(embed=self.get_embed("Error de Formato", f"Parece que has introducido una mención como nombre de equipo.\nUso correcto: `{PREFIX}tourney register <NombreEquipo> <@Miembros...>`", discord.Color.red(), author=ctx.author))
             return

        if active_tourney['status'] != "open":
             await ctx.send(embed=self.get_embed("Error", "El torneo no está abierto para registros.", discord.Color.red(), author=ctx.author))
             return
             
        if await DBManager.get_team_by_name(name, tourney_id):
             await ctx.send(embed=self.get_embed("Error", "Ya existe un equipo con ese nombre.", discord.Color.red(), author=ctx.author))
             return

        # Prepara miembros
        all_members = list(set([ctx.author] + list(members)))
        
        # Valida que no haya miembros repetidos
        for member in all_members:
            existing_team = await DBManager.get_team_by_member(member.id, active_tourney['id'])
            if existing_team:
                await ctx.send(embed=self.get_embed("Error", f"El usuario {member.mention} ya pertenece al equipo **{existing_team['name']}**.\nNo puede unirse a otro equipo.", discord.Color.red()))
                return
        
        # Valida que el equipo tenga entre min_members y max_members miembros
        min_m = active_tourney.get('min_members', 1)
        max_m = active_tourney.get('max_members', 5)
        
        if not (min_m <= len(all_members) <= max_m):
             await ctx.send(embed=self.get_embed("Error", f"El equipo debe tener entre {min_m} y {max_m} miembros (incluyendo al líder).\nSe encontraron: **{len(all_members)}** (Recuerda que el primer argumento es el nombre del equipo).", discord.Color.red(), author=ctx.author))
             return
             
        # Valida que el torneo no tenga el maximo de equipos
        current_teams_count = len(await DBManager.get_teams(tourney_id))
        max_t = active_tourney.get('max_teams', 16)
        if current_teams_count >= max_t:
             await ctx.send(embed=self.get_embed("Error", "El torneo ha alcanzado el límite de equipos.", discord.Color.red(), author=ctx.author))
             return

        member_ids = [m.id for m in all_members]
        
        # Usamos una clase PendingTeam
        if not hasattr(self, 'pending_teams'):
            self.pending_teams = {}
        
        pending_id = str(uuid.uuid4())
        self.pending_teams[pending_id] = {
            "tourney_id": tourney_id,
            "name": name,
            "leader_id": ctx.author.id,
            "members": member_ids,
            "confirmed": [ctx.author.id],
            "message_ids": []
        }
        
        # Envia DMs
        confirm_view = ConfirmRegistrationView(self.bot, pending_id, self)
        
        msgs_sent = 0
        for member in all_members:
            if member.id == ctx.author.id:
                continue 
            
            try:
                await member.send(
                    embed=self.get_embed("Invitación a Equipo", f"Has sido invitado al equipo **{name}** para el torneo **{active_tourney['name']}**.\nConfirma para unirte.", author=ctx.author),
                    view=confirm_view
                )
                msgs_sent += 1
                await self.send_log(
                    ctx.guild, tourney_id,
                    "📩 Invitación Enviada (DM)",
                    f"**Destinatario:** {member.mention}\n**Equipo:** {name}\n**Torneo:** {active_tourney['name']}",
                    discord.Color(0xFFC0CB)
                )
            except discord.Forbidden:
                await ctx.send(f"No pude enviar MD a {member.mention}. Asegúrate de que tengan los MDs abiertos.")
                del self.pending_teams[pending_id]
                return

        if msgs_sent == 0:
            await self.create_team_final(pending_id)
            await ctx.send(embed=self.get_embed("Registro Completado", f"Equipo **{name}** registrado (Solo tú).", author=ctx.author))
        else:
            await ctx.send(embed=self.get_embed("Solicitud Enviada", f"Se ha enviado petición de confirmación a los miembros. El equipo se creará cuando todos acepten.", author=ctx.author))

    async def create_team_final(self, pending_id):
        if pending_id not in self.pending_teams: return
        data = self.pending_teams[pending_id]
        
        new_team = {
            "id": str(uuid.uuid4())[:8],
            "name": data['name'],
            "members": data['members'],
            "leader_id": data['leader_id'],
            "tournament_id": data['tourney_id']
        }
        await DBManager.create_team(new_team)
        
        # Obtener guild para logs
        tourney = await DBManager.get_tournament(data['tourney_id'])
        guild = self.bot.get_guild(tourney['guild_id']) if tourney else None

        # Notifica a todos los miembros
        for uid in data['members']:
            user = self.bot.get_user(uid)
            if not user:
                try:
                    user = await self.bot.fetch_user(uid)
                except:
                    continue
            
            if user:
                try:
                    embed = self.get_embed("Equipo Creado", f"El equipo **{data['name']}** ha sido registrado exitosamente.\nTorneo ID: {data['tourney_id']}", discord.Color.green(), author=user)
                    embed.add_field(name="Líder", value=f"<@{data['leader_id']}>")
                    members_mentions = "\n".join([f"<@{m}>" for m in data['members']])
                    embed.add_field(name="Miembros", value=members_mentions)
                    await user.send(embed=embed)
                    
                    if guild:
                        await self.send_log(
                            guild, data['tourney_id'],
                            "✅ Confirmación de Equipo (DM)",
                            f"**Destinatario:** <@{uid}>\n**Equipo:** {data['name']}\n**Torneo:** {data['tourney_id']}",
                            discord.Color(0xFFC0CB)
                        )
                except discord.Forbidden:
                    pass # DM cerrados

        # Log de creación de equipo
        if guild:
            members_str = ", ".join([f"<@{m}>" for m in data['members']])
            await self.send_log(
                guild, data['tourney_id'],
                "👥 Equipo Creado",
                f"**{data['name']}**\n\n**Líder:** <@{data['leader_id']}>\n**Miembros:** {members_str}",
                discord.Color.blue()
            )

        del self.pending_teams[pending_id]
        
    @tourney.command(name="invite")
    async def invite_member(self, ctx, user: discord.Member):
        # Invita a un usuario a tu equipo (solo el líder puede invitar)
        # Buscar torneo activo
        active_tourney = await DBManager.get_active_tournament(ctx.guild.id)
        if not active_tourney:
            await ctx.send(embed=self.get_embed("Error", "No hay ningún torneo activo en este servidor.", discord.Color.red(), author=ctx.author))
            return
        
        # Verificar que el torneo está abierto para registros
        if active_tourney['status'] != "open":
            await ctx.send(embed=self.get_embed("Error", "El torneo no está abierto para nuevos miembros.", discord.Color.red(), author=ctx.author))
            return
        
        # Buscar el equipo del usuario que invita
        team = await DBManager.get_team_by_member(ctx.author.id, active_tourney['id'])
        if not team:
            await ctx.send(embed=self.get_embed("Error", "No perteneces a ningún equipo en el torneo activo.", discord.Color.red(), author=ctx.author))
            return
            
        if team['leader_id'] != ctx.author.id:
            await ctx.send(embed=self.get_embed("Error", "Solo el líder del equipo puede invitar miembros.", discord.Color.red(), author=ctx.author))
            return
        
        # Verificar límite de miembros
        max_m = active_tourney.get('max_members', 5)
        if len(team['members']) >= max_m:
            await ctx.send(embed=self.get_embed("Error", f"El equipo ya tiene el máximo de miembros permitidos ({max_m}).", discord.Color.red(), author=ctx.author))
            return
             
        # Revisa que el user no esté ya en un equipo
        existing_team = await DBManager.get_team_by_member(user.id, team['tournament_id'])
        if existing_team:
             await ctx.send(embed=self.get_embed("Error", f"El usuario {user.mention} ya está en el equipo **{existing_team['name']}**.", discord.Color.red(), author=ctx.author))
             return

        # Envia DM
        view = ConfirmInviteView(self.bot, team['id'], user.id, self)
        try:
            await user.send(
                embed=self.get_embed("Invitación", f"Te han invitado a unirte al equipo **{team['name']}** en el torneo **{active_tourney['name']}**.", author=ctx.author),
                view=view
            )
            await self.send_log(
                ctx.guild, active_tourney['id'],
                "📩 Invitación a Unirse (DM)",
                f"**Destinatario:** {user.mention}\n**Equipo:** {team['name']}\n**Enviado por:** {ctx.author.mention}",
                discord.Color(0xFFC0CB)
            )
            await ctx.send(embed=self.get_embed("Invitación Enviada", f"Se ha enviado invitación a {user.mention} para unirse al equipo **{team['name']}**.", author=ctx.author))
        except:
             await ctx.send(embed=self.get_embed("Error", f"No se pudo enviar MD a {user.mention}. Asegúrate de que tenga los MDs abiertos.", discord.Color.red(), author=ctx.author))

    @tourney.command(name="kick")
    async def kick_team(self, ctx, tourney_id: str, team_id: str):
        if not await self.admin_check(ctx): return
        
        team = await DBManager.get_team(team_id)
        if not team:
            await ctx.send("Equipo no encontrado.")
            return
        
        team_name = team['name']
        await DBManager.delete_team(team_id)
        
        # Log de eliminación de equipo
        await self.send_log(
            ctx.guild, tourney_id,
            "🗑️ Equipo Eliminado",
            f"**{team_name}**\n\n**Eliminado por:** {ctx.author.mention}",
            discord.Color.orange()
        )
        
        await ctx.send(embed=self.get_embed("Equipo Eliminado", f"El equipo **{team_name}** ha sido expulsado.", author=ctx.author))

    @tourney.command(name="teams")
    async def list_teams(self, ctx, tourney_id: str = None):
         # Si no hay ID, busca el torneo activo
        if not tourney_id:
             t = await DBManager.get_active_tournament(ctx.guild.id)
             if t: tourney_id = t['id']
        
        if not tourney_id:
             await ctx.send(embed=self.get_embed("Error", "Especifica ID de torneo o ten uno activo.", discord.Color.red(), author=ctx.author))
             return

        teams = await DBManager.get_teams(tourney_id)
        if not teams:
             await ctx.send(embed=self.get_embed("Equipos", "No hay equipos registrados.", discord.Color.red(), author=ctx.author))
             return
             
        desc = ""
        for team in teams:
            leader_name = f"<@{team['leader_id']}>"
            desc += f"**{team['name']}** (ID: `{team['id']}`) - Líder: {leader_name} - Miembros: {len(team['members'])}\n"
            
        await ctx.send(embed=self.get_embed(f"Equipos Registrados ({len(teams)})", desc, author=ctx.author))

    @tourney.command(name="team")
    async def team_info(self, ctx, target: str):
        team = None
        # Revisa si el target es una mención o ID
        user = None
        user_id = None
        
        # Revisa menciones primero
        if ctx.message.mentions:
            user_id = ctx.message.mentions[0].id
        else:
            # Intenta parsear como int
            try:
                user_id = int(target)
            except ValueError:
                pass
        
        team = await DBManager.get_team(target)
        
        if not team and user_id:
            # Busca equipo por miembro
            active_t = await DBManager.get_active_tournament(ctx.guild.id)
            if active_t:
                team = await DBManager.get_team_by_member(user_id, active_t['id'])
        
        if not team:
            await ctx.send(embed=self.get_embed("Error", "Equipo no encontrado o usuario no está en un equipo del torneo activo.", discord.Color.red(), author=ctx.author))
            return
            
        members_str = ", ".join([f"<@{m}>" for m in team['members']])
        embed = self.get_embed(f"Info Equipo: {team['name']}", f"ID: {team['id']}\nLíder: <@{team['leader_id']}>", author=ctx.author)
        embed.add_field(name="Miembros", value=members_str)
        
        await ctx.send(embed=embed)

    @tourney.command(name="bug")
    async def report_bug(self, ctx, *, description: str):
        # Reporta un bug o problema del bot
        bug_channel = self.bot.get_channel(BUG_CHANNEL)
        if not bug_channel:
            await ctx.send(embed=self.get_embed("Error", "No se pudo encontrar el canal de bugs.", discord.Color.red(), author=ctx.author))
            return
        
        embed = discord.Embed(
            title="🐛 Reporte de Bug",
            description=description,
            color=discord.Color.red()
        )
        embed.add_field(name="Servidor", value=f"{ctx.guild.name} ({ctx.guild.id})", inline=False)
        embed.add_field(name="Reportado por", value=f"{ctx.author.mention} ({ctx.author.name})", inline=False)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        await bug_channel.send(embed=embed)
        
        # Confirmación al usuario
        confirm_msg = await ctx.send(embed=self.get_embed("Bug Reportado", "Tu reporte ha sido enviado. ¡Gracias por ayudar a mejorar el bot!", discord.Color.green(), author=ctx.author))
        
        # Log al canal de logs del servidor (si está habilitado)
        # Se coge el torneo activo para el ID (si no hay, N/A)
        active_t = await DBManager.get_active_tournament(ctx.guild.id)
        tourney_id = active_t['id'] if active_t else "N/A"
        
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}"
        message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
        
        await self.send_log(
            ctx.guild, tourney_id,
            "🐛 Bug Reportado",
            f"**Descripción:** {description}\n\n**Reportado por:** {ctx.author.mention}\n**Canal:** [#{ctx.channel.name}]({channel_link})\n**Mensaje:** [Ver mensaje]({message_link})",
            discord.Color.red()
        )


class ConfirmRegistrationView(discord.ui.View):
    def __init__(self, bot, pending_id, cog):
        super().__init__(timeout=300)
        self.bot = bot
        self.pending_id = pending_id
        self.cog = cog

    @discord.ui.button(label="Aceptar", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pending_id not in self.cog.pending_teams:
            await interaction.response.send_message("Esta invitación ha expirado o el equipo ya se formó/canceló.", ephemeral=True)
            return

        data = self.cog.pending_teams[self.pending_id]
        if interaction.user.id in data['confirmed']:
            await interaction.response.send_message("Ya has confirmado.", ephemeral=True)
            return

        # Revisa si el usuario se unió a otro equipo en el meantime
        existing = await DBManager.get_team_by_member(interaction.user.id, data['tourney_id'])
        if existing:
             await interaction.response.send_message(f"Ya perteneces al equipo **{existing['name']}**. No puedes unirte a este.", ephemeral=True)
             return

        data['confirmed'].append(interaction.user.id)
        await interaction.response.send_message("Has aceptado unirte al equipo.", ephemeral=True)
        
        # Revisa si todos los miembros confirmaron
        if all(uid in data['confirmed'] for uid in data['members']):
            self.stop()
            try:
                await self.cog.create_team_final(self.pending_id)
            except Exception as e:
                import traceback
                traceback.print_exc()

class ConfirmInviteView(discord.ui.View):
    def __init__(self, bot, team_id, user_id, cog):
        super().__init__(timeout=300)
        self.bot = bot
        self.team_id = team_id
        self.user_id = user_id
        self.cog = cog

    @discord.ui.button(label="Unirse", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
             return
             
        team = await DBManager.get_team(self.team_id)
        if not team:
            await interaction.response.send_message("El equipo ya no existe.", ephemeral=True)
            return
            
        if interaction.user.id in team['members']:
             await interaction.response.send_message("Ya estás en el equipo.", ephemeral=True)
             return
             
        # Revisa si el usuario se unió a otro equipo
        existing = await DBManager.get_team_by_member(interaction.user.id, team['tournament_id'])
        if existing:
             await interaction.response.send_message(f"Ya perteneces al equipo **{existing['name']}**. No puedes unirte a este.", ephemeral=True)
             return
             
        # Añade miembro
        team['members'].append(interaction.user.id)
        from utils.db import teams_collection
        await teams_collection.update_one({"id": self.team_id}, {"$set": {"members": team['members']}})
        
        # Log de miembro unido
        tourney = await DBManager.get_tournament(team['tournament_id'])
        if tourney:
            guild = self.bot.get_guild(tourney['guild_id'])
            if guild:
                await self.cog.send_log(
                    guild, team['tournament_id'],
                    "➕ Miembro Unido",
                    f"**{team['name']}**\n\n**Nuevo miembro:** {interaction.user.mention}\n**Total miembros:** {len(team['members'])}",
                    discord.Color.blue()
                )
        
        await interaction.response.send_message(f"Te has unido a **{team['name']}**!", ephemeral=True)
        self.stop()


async def setup(bot):
    await bot.add_cog(Tourney(bot))

