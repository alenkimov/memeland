from typing import Iterable

import aiohttp

from bot.account import Account, TwitterStatus
from bot.auth import authenticated_memeland, authenticated_twitter
from bot.process import process_accounts_with_session
from bot.logger import logger
from bot.config import CONFIG
from bot.update_info import update_memeland_info, update_twitter_info, update_twitter_status


async def _ensure_twitter_status(
        session: aiohttp.ClientSession,
        account: Account,
):
    async with authenticated_twitter(session, account) as twitter:
        if account.twitter_status == "UNKNOWN":
            await update_twitter_status(twitter, account, "INFO")


def ensure_twitter_status(func):
    async def wrapper(accounts: Iterable[Account]):
        await process_accounts_with_session(accounts, _ensure_twitter_status)
        await func(accounts)

    return wrapper


async def _ensure_twitter_info(
        session: aiohttp.ClientSession,
        account: Account,
):
    async with authenticated_twitter(session, account) as twitter:
        if not account.twitter_info and account.twitter_status == "GOOD":
            await update_twitter_info(twitter, account, "DEBUG")


def ensure_twitter_info(func):
    @filter_accounts_by_twitter_status()
    async def wrapper(accounts: Iterable[Account]):
        await process_accounts_with_session(accounts, _ensure_twitter_info)
        await func(accounts)

    return wrapper


async def _ensure_memeland_info(
        session: aiohttp.ClientSession,
        account: Account,
):
    if not account.memeland_info or not account.tasks:
        async with authenticated_memeland(session, account) as memeland:
            await update_memeland_info(memeland, account, "INFO")


def ensure_memeland_info(func):
    async def wrapper(accounts: Iterable[Account]):
        await process_accounts_with_session(accounts, _ensure_memeland_info)
        await func(accounts)

    return wrapper


def filter_accounts_by_twitter_status(
        statuses: Iterable[TwitterStatus] = ("GOOD", ),
        blacklist: bool = False,
):
    def decorator(func):

        @ensure_twitter_status
        async def wrapper(accounts: Iterable[Account]):
            filtered_accounts = []

            for account in accounts:
                if blacklist:
                    if account.twitter_status not in statuses:
                        filtered_accounts.append(account)
                else:
                    if account.twitter_status in statuses:
                        filtered_accounts.append(account)

            if not filtered_accounts:
                logger.warning(f"(blacklist={blacklist}, statuses={statuses})"
                               f" Ни один из аккаунтов не подходит под критерии.")

            await func(filtered_accounts)

        return wrapper

    return decorator


def filter_accounts_by_twitter_info(
        minimum_age: int = None,
        minimum_followers_count: int = None,
):
    def decorator(func):

        @ensure_twitter_info
        async def wrapper(accounts: Iterable[Account]):
            filtered_accounts = []
            for account in accounts:
                is_filtered = False

                if minimum_followers_count and account.followers_count < minimum_followers_count:
                    logger.warning(f"{account} {account.followers_count} из {minimum_followers_count} подписчиков")
                    if not CONFIG.IGNORE_WARNINGS:
                        is_filtered = True

                if minimum_age and account.twitter_account_age < minimum_age:
                    logger.warning(f"{account} Возраст аккаунта: {account.twitter_account_age} дней")
                    if not CONFIG.IGNORE_WARNINGS:
                        is_filtered = True

                if not is_filtered:
                    filtered_accounts.append(account)

            if not filtered_accounts:
                logger.warning(f"(minimum_age={minimum_age}, minimum_followers_count={minimum_followers_count})"
                               f" Ни один из аккаунтов не подходит под критерии.")

            await func(filtered_accounts)

        return wrapper

    return decorator


def filter_accounts_by_token(token_name: str, *, presence: bool):
    def decorator(func):
        async def wrapper(accounts: Iterable[Account]):
            if not accounts:
                return

            if presence:
                filtered_accounts = [account for account in accounts if token_name in account.auth_tokens]
                log_message = f"No accounts with {token_name} token"
            else:
                filtered_accounts = [account for account in accounts if token_name not in account.auth_tokens]
                log_message = f"All accounts have {token_name} token"

            if not filtered_accounts:
                logger.warning(log_message)
                return

            return await func(filtered_accounts)

        return wrapper

    return decorator


def filter_accounts_by_memeland_info(
        wallet_is_linked: bool = False,
):
    def decorator(func):

        @ensure_memeland_info
        async def wrapper(accounts: Iterable[Account]):
            filtered_accounts = []
            for account in accounts:
                is_filtered = False

                if account.wallet_is_linked != wallet_is_linked:
                    is_filtered = True

                if not is_filtered:
                    filtered_accounts.append(account)

            await func(filtered_accounts)

        return wrapper

    return decorator
