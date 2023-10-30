import asyncio
from collections import defaultdict
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
        if e.code == 429:
            raise
        logger.warning(f"{account} {e}")
        return


async def process_account_with_proxy(
        account: Account,
        fn: Callable,
        *,
        proxy: Proxy = None,
):
    connector = ProxyConnector.from_url(proxy.as_url) if proxy else aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        await process_account_with_session(session, account, fn)


async def process_accounts_with_session(
        accounts: Iterable[Account],
        fn: Callable,
        *,
        max_tasks: int = 1,
        max_tasks_per_proxy: int = 1,
        default_proxy: Proxy = None,
):
    """
    :param accounts: Аккаунты.
    :param fn: Асинхронная функция для обработки аккаунта.
     Должна принимать первым параметров сессию aiohttp.ClientSession, а вторым - аккаунт.
    :param max_tasks: Максимальное количество одновременно обрабатываемых аккаунтов.
    :param max_tasks_per_proxy: Ограничивает максимальное количество одновременно
     обрабатываемых аккаунтов на одном и том же прокси.
    :param default_proxy: Если у аккаунта отсутствует прокси,
     то будет применено прокси по умолчанию.
    """

    # TODO Осторожно, костыль
    max_tasks = CONFIG.MAX_TASKS
    max_tasks_per_proxy = CONFIG.MAX_TASKS_PER_PROXY
    default_proxy = Proxy.from_str(CONFIG.DEFAULT_PROXY)

    proxy_to_accounts: dict[Proxy, list[Account]] = defaultdict(list)
    for account in accounts:
        proxy = account.proxy or default_proxy
        proxy_to_accounts[proxy].append(account)

    semaphores: dict[Proxy, asyncio.Semaphore] = {
        proxy: asyncio.Semaphore(max_tasks_per_proxy) for proxy in proxy_to_accounts
    }
    global_semaphore = asyncio.Semaphore(max_tasks)

    async def process_with_limit(account: Account, proxy: Proxy):
        async with global_semaphore:
            async with semaphores[proxy]:
                await process_account_with_proxy(account, fn, proxy=proxy)

    tasks = [
        asyncio.create_task(process_with_limit(account, proxy))
        for proxy, accounts_list in proxy_to_accounts.items()
        for account in accounts_list
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    # Если какая-то из задач завершилась с ошибкой, прерываем остальные задачи
    for task in done:
        exc = task.exception()
        if isinstance(exc, aiohttp.ContentTypeError):
            logger.error(f"Вместо ответа пришел HTML. Попробуйте позже")
        elif isinstance(exc, MemelandAPIError) and exc.code == 429:
            logger.warning(f"{exc}. Попробуйте позже")
        elif exc:
            logger.error(f"Непредвиденная ошибка: {exc}")
            logger.exception(exc)
        # Отменяем оставшиеся задачи
        for p in pending:
            p.cancel()
