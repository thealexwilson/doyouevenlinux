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
"""The path to the cache file."""

CACHE_INVALIDATION_DAYS = 7
"""The number of days until a cached game is invalid."""

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
"""Cache timestamp format."""


class Cache:
    """Cache wrapper class.

    Includes methods to aid with loading, updating, pruning, etc.
    """

    def __init__(self) -> None:
        """Construct a new Cache object."""
        self.cache_path: Path = CACHE_PATH
        self._games_data: dict[str, tuple[Game, str]] = {}
        self._anti_cheat_data: dict[str, AntiCheatData] = {}
        self._anti_cheat_timestamp: str = ''
        self._protondb_data: dict[str, str] = {}  # app_id -> rating

    @override
    def __repr__(self) -> str:
        """Return the string representation of the Cache object."""
        return f'Cache({self.__dict__!r})'

    def _serialize_game_data(self) -> dict[str, SerializedGameData]:
        """Serialize the game data into a valid JSON dict."""
        return {
            app_id: {
                'name': game[0].name,
                'rating': game[0].rating,
                'timestamp': game[1],
            }
            for app_id, game in self._games_data.items()
        }

    def _serialize_anti_cheat_data(self) -> SerializedAnticheatData:
        """Serialize the anticheat data into a valid JSON dict."""
        return {
            'data': {
                app_id: ac_data.status.value
                for app_id, ac_data in self._anti_cheat_data.items()
            },
            'timestamp': self._anti_cheat_timestamp,
        }

    def _serialize_protondb_data(self) -> dict[str, str]:
        """Serialize ProtonDB data for storing in JSON."""
        return self._protondb_data

    @property
    def has_game_cache(self) -> bool:
        """Whether or not there is game cache loaded."""
        return bool(self._games_data)

    @property
    def has_anticheat_cache(self) -> bool:
        """Whether or not there is anticheat cache loaded."""
        return bool(self._anti_cheat_data)

    def get_game_data(self, app_id: str) -> Game | None:
        """Get game data from app ID."""
        data = self._games_data.get(app_id, None)
        if data is not None:
            return data[0]
        return None

    def get_protondb_rating(self, app_id: str) -> str | None:
        """Return the cached ProtonDB rating for a game if available."""
        return self._protondb_data.get(app_id)

    def get_anticheat_data(self, app_id: str) -> AntiCheatData | None:
        """Get anticheat data from app ID."""
        data = self._anti_cheat_data.get(app_id, None)
        if data is not None:
            return data
        return None

    def load_cache(self, prune: bool = True) -> Self:
        """Load and deserialize the cache."""
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

        if 'protondb_cache' in data:
            self._protondb_data = data['protondb_cache']

        return self

    def update_cache(
        self,
        game_list: list[Game] | None = None,
        anti_cheat_list: list[AntiCheatData] | None = None,
        protondb_data: dict[str, str] | None = None,
    ) -> Self:
        """Update the cache file with new game, anticheat, and ProtonDB data."""
        self.load_cache()

        if game_list:
            for game in game_list:
                timestamp = self._games_data.get(game.app_id, ("", ""))[1] or datetime.now().strftime(TIMESTAMP_FORMAT)
                self._games_data[game.app_id] = (game, timestamp)

        if anti_cheat_list:
            for ac in anti_cheat_list:
                self._anti_cheat_data[ac.app_id] = ac
            self._anti_cheat_timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)

        if protondb_data:
            self._protondb_data.update(protondb_data)

        serialized_data = {
            'game_cache': self._serialize_game_data(),
            'anticheat_cache': self._serialize_anti_cheat_data(),
            'protondb_cache': self._serialize_protondb_data(),
        }

        self.cache_path.write_text(json.dumps(serialized_data))

        return self

    def prune_cache(self) -> Self:
        """Remove the old entries from the cache file."""
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

        if 'protondb_cache' in data:
            # Remove old ProtonDB ratings
            protondb_keys = list(data['protondb_cache'].keys())
            for key in protondb_keys:
                # we don’t have timestamps, so just rely on invalidation period for all games
                # if the cache is older than CACHE_INVALIDATION_DAYS we could reset entirely
                pass  # could extend later with timestamps if desired

        self.cache_path.write_text(json.dumps(data))

        return self