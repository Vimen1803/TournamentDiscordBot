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
    tourney_log_channel_id: Optional[int] = None
    tourney_logs: Optional[bool] = None
    prefix: Optional[str] = None
    admin_roles: List[str] = None
    invite_url: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Team:
    id: str
    name: str
    members: List[int]
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
    id: str
    name: str
    guild_id: int
    settings: Dict
    status: str
    current_round: int
    matches: List[List[Dict]]
    created_at: datetime.datetime
    description: str = ""
    date: str = ""
    registration_end_time: str = ""
    start_time: str = ""
    max_teams: int = 16
    min_members: int = 1
    max_members: int = 5
    image_url: Optional[str] = None
    winner_id: Optional[str] = None
    last_bracket_url: Optional[str] = None

    def to_dict(self):
        return asdict(self)

class DBManager:
    @staticmethod
    async def create_tournament(data: dict):
        """
        Crea un nuevo torneo
        """
        result = await tournaments_collection.insert_one(data)
        return result.inserted_id

    @staticmethod
    async def get_tournament(tournament_id: str):
        """
        Obtiene un torneo por su ID
        """
        return await tournaments_collection.find_one({"id": tournament_id})

    @staticmethod
    async def get_active_tournament(guild_id: int):
        """
        Obtiene el torneo activo de un servidor
        """
        return await tournaments_collection.find_one({"guild_id": guild_id, "status": {"$in": ["open", "active", "pending"]}})

    @staticmethod
    async def update_tournament(tournament_id: str, update_data: dict):
        """
        Actualiza un torneo
        """
        await tournaments_collection.update_one({"id": tournament_id}, {"$set": update_data})

    @staticmethod
    async def create_team(data: dict):
        """
        Crea un nuevo equipo
        """
        result = await teams_collection.insert_one(data)
        return result.inserted_id

    @staticmethod
    async def get_team(team_id: str):
        """
        Obtiene un equipo por su ID
        """
        return await teams_collection.find_one({"id": team_id})
    
    @staticmethod
    async def get_team_by_name(name: str, tournament_id: str):
        """
        Obtiene un equipo por su nombre
        """
        return await teams_collection.find_one({"name": name, "tournament_id": tournament_id})

    @staticmethod
    async def get_team_by_member(user_id: int, tournament_id: str = None):
        """
        Obtiene un equipo por el ID de uno de sus miembros
        """
        query = {"members": user_id}
        if tournament_id:
            query["tournament_id"] = tournament_id
        return await teams_collection.find_one(query)

    @staticmethod
    async def get_teams(tournament_id: str):
        """
        Obtiene todos los equipos de un torneo
        """
        cursor = teams_collection.find({"tournament_id": tournament_id})
        return await cursor.to_list(length=None)

    @staticmethod
    async def delete_team(team_id: str):
        """
        Elimina un equipo
        """
        await teams_collection.delete_one({"id": team_id})

    @staticmethod
    async def update_team(team_id: str, data: dict):
        """
        Actualiza un equipo
        """
        await teams_collection.update_one({"id": team_id}, {"$set": data})

    @staticmethod
    async def delete_tournament(tournament_id: str):
        """
        Elimina un torneo de la base de datos
        """
        await tournaments_collection.delete_one({"id": tournament_id})

    @staticmethod
    async def delete_teams_by_tournament(tournament_id: str):
        """
        Elimina todos los equipos de un torneo
        """
        await teams_collection.delete_many({"tournament_id": tournament_id})

    @staticmethod
    async def get_tournaments_history(guild_id: int, skip: int = 0, limit: int = 1):
        """
        Obtiene el historial de torneos de un servidor
        """
        cursor = tournaments_collection.find({"guild_id": guild_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def count_tournaments(guild_id: int):
        """
        Cuenta el número de torneos de un servidor
        """
        return await tournaments_collection.count_documents({"guild_id": guild_id})

    @staticmethod
    async def count_tournaments(guild_id: int):
        """
        Cuenta el número de torneos de un servidor
        """
        return await tournaments_collection.count_documents({"guild_id": guild_id})

    @staticmethod
    async def get_guild_config(guild_id: int):
        """
        Obtiene la configuración de un servidor
        """
        return await guilds_config_collection.find_one({"guild_id": guild_id})

    @staticmethod
    async def get_or_create_guild_config(guild_id: int):
        """
        Obtiene la configuración de un servidor o la crea si no existe
        """
        config = await guilds_config_collection.find_one({"guild_id": guild_id})
        if not config:
            new_config = GuildConfig(guild_id=guild_id, admin_roles=[])
            await guilds_config_collection.insert_one(new_config.to_dict())
            return new_config.to_dict()
        return config

    @staticmethod
    async def update_guild_config_field(guild_id: int, field: str, value):
        """
        Actualiza un campo de la configuración de un servidor
        """
        await DBManager.get_or_create_guild_config(guild_id)
        await guilds_config_collection.update_one({"guild_id": guild_id}, {"$set": {field: value}})
