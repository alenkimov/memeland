import asyncio
from typing import Callable, Iterable

import questionary
from better_automation.utils import load_toml, load_lines
from better_proxy import Proxy

from bot.logger import logger, setup_logger
from bot.paths import LOG_DIR, TOKENS_TXT, ACCOUNTS_JSON
from bot.config import CONFIG
from bot.author import TG_LINK
from bot.account import extract_or_create_accounts, Account
from bot.scripts import auth_accounts, link_wallets

PROJECT_INFO = load_toml('pyproject.toml')
PROJECT_VERSION = PROJECT_INFO['tool']['poetry']['version']


def print_script_info():
    print(f'VERSION {PROJECT_VERSION}')
    print(f"Telegram: {TG_LINK}")


def print_total_points(accounts: Iterable[Account]):
    total_points = sum((account.points for account in accounts if account.points))
    print(f"Total points: {total_points}")


async def select_module(modules) -> Callable:
    module_name = await questionary.select("Select module:", choices=list(modules.keys())).ask_async()
    return modules[module_name]


async def main():
    setup_logger(LOG_DIR, console_logging_level=CONFIG.LOGGING_LEVEL)

    twitter_auth_tokens = load_lines(TOKENS_TXT)

    if not twitter_auth_tokens:
        logger.warning(f"No twitter auth tokens ('{TOKENS_TXT}')")
        return

    logger.info(f"Total twitter auth tokens: {len(twitter_auth_tokens)}")

    proxy = None
    if CONFIG.PROXY:
        proxy = Proxy.from_str(CONFIG.PROXY)

    accounts = extract_or_create_accounts(twitter_auth_tokens, ACCOUNTS_JSON, proxy)

    modules = {
        'Exit': None,
        '[1] Auth accounts': auth_accounts,
        '[2] Link wallets': link_wallets,
    }

    while True:
        print_script_info()
        print_total_points(accounts)
        module = await select_module(modules)

        if module is None:
            break

        await module(accounts)


if __name__ == '__main__':
    asyncio.run(main())
