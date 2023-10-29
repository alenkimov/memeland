from typing import Iterable

from better_automation.utils.file import write_lines

from bot.account import Account
from bot.paths import REGISTERED_TXT
from bot.logger import logger
from bot.filters import filter_accounts_by_memeland_info


@filter_accounts_by_memeland_info(wallet_is_linked=True)
async def make_output(accounts: Iterable[Account]):
    accounts_to_write = [f'{account.auth_tokens["twitter"]}:{account.wallet.private_key}' for account in accounts]
    write_lines(REGISTERED_TXT, accounts_to_write)
    logger.success(f"Зарегистрированные аккаунты сохранены по пути {REGISTERED_TXT}")
