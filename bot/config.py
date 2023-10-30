from better_automation.utils import load_toml
from pydantic import BaseModel

from bot.logger import LoggingLevel
from bot.paths import CONFIG_TOML


class Config(BaseModel):
    LOGGING_LEVEL: LoggingLevel = "INFO"
    IGNORE_WARNINGS: bool = False
    # DELAY_RANGE: tuple[int, int] = (0, 0)
    MAX_TASKS: int = 5
    MAX_TASKS_PER_PROXY: int = 5

    DEFAULT_PROXY: str | None = None  # Должен быть типа Proxy
    CHANGE_PROXY_URL: str | None = None

    # CAPTCHA_SERVICE: CaptchaSolvingService
    # CAPTCHA_SERVICE_API_KEY: str

    NFT: str | None = None

    MINIMUM_ACCOUNT_AGE_IN_DAYS: int = 30
    MINIMUM_FOLLOWERS_COUNT: int = 3


CONFIG = Config(**load_toml(CONFIG_TOML))
