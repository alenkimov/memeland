import asyncio
from random import randrange
from typing import Iterable, Callable

import aiohttp
from aiohttp_socks import ProxyConnector
from better_automation.process import bounded_gather
from better_proxy import Proxy

from bot.config import CONFIG
from bot.logger import logger, LoggingLevel
from bot.account import Account
from bot.paths import ACCOUNTS_JSON

from bot.api import MemelandAPIError
from better_automation.twitter.errors import HTTPException as TwitterException


async def sleep(account, seconds: int, logging_level: LoggingLevel = "DEBUG"):
    if seconds <= 0:
        return

    logger.log(logging_level, f"{account} Sleeping {seconds} sec.")
    await asyncio.sleep(seconds)


async def process_account_with_session(
        session: aiohttp.ClientSession,
        account: Account,
        fn: Callable,
        ignore_errors: bool = False,
):
    try:
        await fn(session, account)
    except TwitterException as e:
        if any(code in e.api_codes for code in (32, )):
            account.twitter_status = "BAD_TOKEN"
            account.save(ACCOUNTS_JSON)
        if any(code in e.api_codes for code in (64, )):
            account.twitter_status = "BANNED"
            account.save(ACCOUNTS_JSON)
        if any(code in e.api_codes for code in (326, )):
            account.twitter_status = "LOCKED"
            account.save(ACCOUNTS_JSON)
    except MemelandAPIError as e:
        logger.warning(f"{account} {e}")
        return
    except Exception as e:
        logger.error(f"{account} Непредвиденная ошибка: {e}")
        if ignore_errors:
            return
        else:
            raise


async def _process_accounts_with_session(
        accounts: Iterable[Account],
        fn: Callable,
        *,
        proxy: Proxy = None,
):
    connector = ProxyConnector.from_url(proxy) if proxy else aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        accounts_len = len(list(accounts))
        for account in accounts:
            await process_account_with_session(session, account, fn)
            if accounts_len > 1 and sum(CONFIG.DELAY_RANGE) > 0:
                await sleep(account, randrange(*CONFIG.DELAY_RANGE), logging_level="INFO")


async def process_accounts_with_session(
        accounts: Iterable[Account],
        fn: Callable,
        max_tasks: int = None,
):
    proxy_to_accounts: dict[Proxy: list[accounts]] = {}
    for account in accounts:
        if account.proxy not in proxy_to_accounts:
            proxy_to_accounts[account.proxy] = []
        proxy_to_accounts[account.proxy].append(account)
    tasks = [_process_accounts_with_session(accounts, fn)
             for accounts in proxy_to_accounts.values()]
    max_tasks = max_tasks or CONFIG.MAX_TASKS
    await bounded_gather(tasks, max_tasks)
