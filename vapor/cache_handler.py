"""Vapor cache handling."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import cast

from typing_extensions import Self, override

from vapor.data_structures import (
    CONFIG_DIR,
    AntiCheatData,
    AntiCheatStatus,
    CacheFile,
    Game,
    SerializedAnticheatData,
    SerializedGameData,
)

CACHE_PATH = CONFIG_DIR / 'cache.json'
CACHE_INVALIDATION_DAYS = 7
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


class Cache:
    """Cache wrapper class for local JSON cache (games + anticheat)."""

    def __init__(self) -> None:
        self.cache_path: Path = CACHE_PATH
        self._games_data: dict[str, tuple[Game, str]] = {}
        self._anti_cheat_data: dict[str, AntiCheatData] = {}
        self._anti_cheat_timestamp: str = ''

    @override
    def __repr__(self) -> str:
        return f'Cache({self.__dict__!r})'

    def _serialize_game_data(self) -> dict[str, SerializedGameData]:
        return {
            app_id: {
                'name': game[0].name,
                'rating': game[0].rating,
                'timestamp': game[1],
            }
            for app_id, game in self._games_data.items()
        }

    def _serialize_anti_cheat_data(self) -> SerializedAnticheatData:
        return {
            'data': {
                app_id: ac_data.status.value
                for app_id, ac_data in self._anti_cheat_data.items()
            },
            'timestamp': self._anti_cheat_timestamp,
        }

    @property
    def has_game_cache(self) -> bool:
        return bool(self._games_data)

    @property
    def has_anticheat_cache(self) -> bool:
        return bool(self._anti_cheat_data)

    def get_game_data(self, app_id: str) -> Game | None:
        return self._games_data.get(app_id, (None, ""))[0]

    def get_anticheat_data(self, app_id: str) -> AntiCheatData | None:
        return self._anti_cheat_data.get(app_id)

    def load_cache(self, prune: bool = True) -> Self:
        if prune:
            self.prune_cache()

        try:
            data = cast(CacheFile, json.loads(self.cache_path.read_text()))
        except Exception:
            return self

        if 'game_cache' in data:
            self._games_data = {
                app_id: (
                    Game(
                        game_cache['name'],
                        rating=game_cache['rating'],
                        playtime=0,
                        app_id=app_id,
                    ),
                    game_cache['timestamp'],
                )
                for app_id, game_cache in data['game_cache'].items()
            }

        if 'anticheat_cache' in data:
            self._anti_cheat_data = {
                app_id: AntiCheatData(app_id=app_id, status=AntiCheatStatus(status))
                for app_id, status in data['anticheat_cache']['data'].items()
            }
            self._anti_cheat_timestamp = data['anticheat_cache']['timestamp']

        return self

    def update_cache(
        self,
        game_list: list[Game] | None = None,
        anti_cheat_list: list[AntiCheatData] | None = None,
    ) -> Self:
        """Update only local JSON cache. ProtonDB now lives in Redis."""
        self.load_cache()

        if game_list:
            for game in game_list:
                timestamp = self._games_data.get(game.app_id, ("", ""))[1] or datetime.now().strftime(TIMESTAMP_FORMAT)
                self._games_data[game.app_id] = (game, timestamp)

        if anti_cheat_list:
            for ac in anti_cheat_list:
                self._anti_cheat_data[ac.app_id] = ac
            self._anti_cheat_timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)

        serialized_data = {
            'game_cache': self._serialize_game_data(),
            'anticheat_cache': self._serialize_anti_cheat_data(),
        }

        self.cache_path.write_text(json.dumps(serialized_data))
        return self

    def prune_cache(self) -> Self:
        try:
            data = cast(CacheFile, json.loads(self.cache_path.read_text()))
        except Exception:
            return self

        if 'game_cache' in data:
            for app_id, val in list(data['game_cache'].items()):
                try:
                    parsed_date = datetime.strptime(val['timestamp'], TIMESTAMP_FORMAT)
                    if (datetime.now() - parsed_date).days > CACHE_INVALIDATION_DAYS:
                        del data['game_cache'][app_id]
                except ValueError:
                    del data['game_cache'][app_id]

        if 'anticheat_cache' in data:
            try:
                parsed_date = datetime.strptime(data['anticheat_cache']['timestamp'], TIMESTAMP_FORMAT)
                if (datetime.now() - parsed_date).days > CACHE_INVALIDATION_DAYS:
                    del data['anticheat_cache']
            except ValueError:
                del data['anticheat_cache']

        self.cache_path.write_text(json.dumps(data))
        return self