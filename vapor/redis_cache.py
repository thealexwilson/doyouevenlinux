# vapor/redis_cache.py
from upstash_redis import Redis
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load from environment
redis_client = Redis.from_env()

def set_cached_rating(app_id: str, rating: str) -> None:
    """Set ProtonDB rating in Upstash Redis (sync)."""
    # redis_client.set(f"protondb:{app_id}", rating)
    try:
        redis_client.set(f"protondb:{app_id}", rating)
        logger.debug(f"SET protondb:{app_id} = {rating}")
    except Exception as e:
        logger.error(f"Failed to set protondb:{app_id}: {e}")

def get_protondb_rating(app_id: str) -> str | None:
    """Get ProtonDB rating from Upstash Redis (sync)."""
    # value = redis_client.get(f"protondb:{app_id}")
    # if value is not None:
    #     return value
    # return None
    try:
        value = redis_client.get(f"protondb:{app_id}")
        logger.debug(f"GET protondb:{app_id} -> {value}")
        if value is not None:
            return value
        return None
    except Exception as e:
        logger.error(f"Failed to get protondb:{app_id}: {e}")
        return None