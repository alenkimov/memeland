from better_automation.utils import load_toml
from pydantic import BaseModel

from bot.logger import LoggingLevel
from bot.paths import CONFIG_TOML


class Config(BaseModel):
    LOGGING_LEVEL: LoggingLevel = "INFO"
    IGNORE_WARNINGS: bool = False
    DELAY_RANGE: tuple[int, int] = (0, 0)
    MAX_TASKS: int = 5

    PROXY: str | None = None
    # CHANGE_PROXY_URL: str | None = None

    # CAPTCHA_SERVICE: CaptchaSolvingService
    # CAPTCHA_SERVICE_API_KEY: str

    NFT: str = "..."
    MINIMUM_ACCOUNT_AGE_IN_DAYS: int = 30


CONFIG = Config(**load_toml(CONFIG_TOML))
