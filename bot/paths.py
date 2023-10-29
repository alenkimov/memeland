from pathlib import Path
from better_automation.utils import copy_file


SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent

SETTINGS_DIR = BASE_DIR / "settings"
CONFIG_DIR = BASE_DIR / "config"
DEFAULT_CONFIG_DIR = CONFIG_DIR / ".default"
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"
ABI_DIR = SCRIPT_DIR / "abi"

DIRS = (INPUT_DIR, OUTPUT_DIR, DATA_DIR, LOG_DIR)

for dir in DIRS:
    dir.mkdir(exist_ok=True)

TOKENS_TXT = INPUT_DIR / "auth_tokens.txt"
ACCOUNTS_JSON = DATA_DIR / "accounts.json"

FILES = (TOKENS_TXT, ACCOUNTS_JSON)
for file in FILES:
    file.touch()

DEFAULT_CONFIG_TOML = DEFAULT_CONFIG_DIR / "config.toml"
CONFIG_TOML = CONFIG_DIR / "config.toml"
copy_file(DEFAULT_CONFIG_TOML, CONFIG_TOML)
