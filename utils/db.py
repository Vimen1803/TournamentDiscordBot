import motor.motor_asyncio
from config import URL_BASE_1
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import datetime

# Conexión a MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(URL_BASE_1)
db = client['tourney_bot']
tournaments_collection = db['tournaments']
teams_collection = db['teams']
guilds_config_collection = db['guild_config']

@dataclass
class GuildConfig:
    guild_id: int
    category_id: Optional[int] = None
    bracket_channel_id: Optional[int] = None
    lobby_channel_id: Optional[int] = None
    bot_admin_channel_id: Optional[int] = None
    admin_roles: List[str] = None # Lista de roles IDs como strings

    def to_dict(self):
        return asdict(self)

@dataclass
class Team:
    id: str  # ID generado
    name: str
    members: List[int] # IDs de los miembros
    leader_id: int
    tournament_id: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Match:
    team1_id: Optional[str]
    team2_id: Optional[str]
    winner_id: Optional[str] = None
    channel_id: Optional[int] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Tournament:
    id: str # ID generado
    name: str # Generalmente el nombre del servidor o personalizado
    guild_id: int # ID del servidor
    settings: Dict # category_id, bracket_channel_id, lobby_channel_id, bot_admin_channel_id, admin_role_ids
    status: str # "open", "active", "finished"
    current_round: int # El número de la ronda actual
    matches: List[List[Dict]] # Lista de rondas
    created_at: datetime.datetime
    # Nuevos campos
    description: str = ""
    start_date: str = "" # Almacenado como string para mostrar
    max_teams: int = 16
    min_members: int = 1
    max_members: int = 5
    image_url: Optional[str] = None
    winner_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)

class DBManager:
    @staticmethod
    async def create_tournament(data: dict):
        result = await tournaments_collection.insert_one(data)
        return result.inserted_id

    @staticmethod
    async def get_tournament(tournament_id: str):
        return await tournaments_collection.find_one({"id": tournament_id})

    @staticmethod
    async def get_active_tournament(guild_id: int):
        # Asumiendo un activo por server por simplificación, o buscar por ID
        return await tournaments_collection.find_one({"guild_id": guild_id, "status": {"$in": ["open", "active"]}})

    @staticmethod
    async def update_tournament(tournament_id: str, update_data: dict):
        await tournaments_collection.update_one({"id": tournament_id}, {"$set": update_data})

    @staticmethod
    async def create_team(data: dict):
        result = await teams_collection.insert_one(data)
        return result.inserted_id

    @staticmethod
    async def get_team(team_id: str):
        return await teams_collection.find_one({"id": team_id})
    
    @staticmethod
    async def get_team_by_name(name: str, tournament_id: str):
        return await teams_collection.find_one({"name": name, "tournament_id": tournament_id})

    @staticmethod
    async def get_team_by_member(user_id: int, tournament_id: str = None):
        query = {"members": user_id}
        if tournament_id:
            query["tournament_id"] = tournament_id
        return await teams_collection.find_one(query)

    @staticmethod
    async def get_teams(tournament_id: str):
        cursor = teams_collection.find({"tournament_id": tournament_id})
        return await cursor.to_list(length=None)

    @staticmethod
    async def delete_team(team_id: str):
        await teams_collection.delete_one({"id": team_id})

    @staticmethod
    async def delete_tournament(tournament_id: str):
        """Elimina un torneo de la base de datos"""
        await tournaments_collection.delete_one({"id": tournament_id})

    @staticmethod
    async def delete_teams_by_tournament(tournament_id: str):
        """Elimina todos los equipos de un torneo"""
        await teams_collection.delete_many({"tournament_id": tournament_id})

    @staticmethod
    async def get_tournaments_history(guild_id: int, skip: int = 0, limit: int = 1):
        cursor = tournaments_collection.find({"guild_id": guild_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def count_tournaments(guild_id: int):
        return await tournaments_collection.count_documents({"guild_id": guild_id})

    @staticmethod
    async def count_tournaments(guild_id: int):
        return await tournaments_collection.count_documents({"guild_id": guild_id})

    @staticmethod
    async def get_guild_config(guild_id: int):
        return await guilds_config_collection.find_one({"guild_id": guild_id})

    @staticmethod
    async def get_or_create_guild_config(guild_id: int):
        config = await guilds_config_collection.find_one({"guild_id": guild_id})
        if not config:
            new_config = GuildConfig(guild_id=guild_id, admin_roles=[])
            await guilds_config_collection.insert_one(new_config.to_dict())
            return new_config.to_dict()
        return config

    @staticmethod
    async def update_guild_config_field(guild_id: int, field: str, value):
        # Se asegura de que exista la configuración
        await DBManager.get_or_create_guild_config(guild_id)
        await guilds_config_collection.update_one({"guild_id": guild_id}, {"$set": {field: value}})
