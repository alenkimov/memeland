from typing import Iterable

import aiohttp

from bot.account import Account, TwitterStatus
from bot.api import MemelandAPI
from bot.auth import authenticated_memeland, authenticated_twitter, auth_memeland
from bot.process import process_accounts_with_session
from bot.logger import logger, LoggingLevel
from bot.config import CONFIG
from bot.paths import ACCOUNTS_JSON


async def _ensure_twitter_info(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    if not account.twitter_info:
        async with authenticated_twitter(session, account) as twitter:
            twitter_username = await twitter.request_username()
            account.twitter_info = await twitter.request_user_info(twitter_username)
            account.save(ACCOUNTS_JSON)
            logger.log(logging_level, f"{account} Информация о Твиттер аккаунте успешно запрошена")


async def _request_memeland_info(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    async with authenticated_memeland(session, account) as memeland:
        account.memeland_info = await memeland.request_info()
        account.tasks = await memeland.request_tasks()
        account.save(ACCOUNTS_JSON)
        logger.log(logging_level, f"{account} Информация об аккаунте Memeland и тасках успешно запрошена")


async def _ensure_memeland_info(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    if not account.memeland_info or not account.tasks:
        await _request_memeland_info(session, account, logging_level)


def ensure_twitter_info(func):
    async def wrapper(accounts: Iterable[Account]):
        await process_accounts_with_session(accounts, _ensure_twitter_info)
        await func(accounts)

    return wrapper


def ensure_memeland_info(func):
    async def wrapper(accounts: Iterable[Account]):
        await process_accounts_with_session(accounts, _ensure_memeland_info)
        await func(accounts)

    return wrapper


def filter_accounts(
        minimum_age: int = None,
        minimum_followers_count: int = None,
        twitter_statuses_blacklist: Iterable[TwitterStatus] = None,
        account_is_authed: bool = None,
        wallet_is_linked: bool = None,
):
    def decorator(func):
        async def wrapper(accounts: Iterable[Account]):
            filtered_accounts = []
            for account in accounts:
                is_filtered = False

                if twitter_statuses_blacklist and account.twitter_status in twitter_statuses_blacklist:
                    logger.warning(f"{account} Twitter status {account.twitter_info} is blacklisted")
                    is_filtered = True

                if minimum_followers_count and account.followers_count < minimum_followers_count:
                    logger.warning(f"{account} {account.followers_count} из {minimum_followers_count} подписчиков")
                    if not CONFIG.IGNORE_WARNINGS:
                        is_filtered = True

                if minimum_age and account.twitter_account_age < minimum_age:
                    logger.warning(f"{account} Возраст аккаунта: {account.twitter_account_age} дней")
                    if not CONFIG.IGNORE_WARNINGS:
                        is_filtered = True

                if account_is_authed is not None and account.is_authed != account_is_authed:
                    # logger.warning(f"{account} Account authentication status mismatch")
                    is_filtered = True

                if wallet_is_linked is not None and account.wallet_is_linked != wallet_is_linked:
                    # logger.warning(f"{account} Wallet linking status mismatch")
                    is_filtered = True

                if not is_filtered:
                    filtered_accounts.append(account)

            await func(filtered_accounts)

        return wrapper

    return decorator


async def _auth_account(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "SUCCESS",
):
    async with authenticated_twitter(session, account) as twitter:
        await auth_memeland(session, twitter, account, logging_level)
    await _request_memeland_info(session, account)


async def _link_wallet(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "SUCCESS",
):
    address = account.wallet.address
    twitter_username = account.memeland_info["twitter"]["username"]
    message = (f"This wallet willl be dropped $MEME from your harvested MEMEPOINTS."
               f" If you referred friends, family, lovers or strangers, ensure this wallet has the NFT you referred."
               f"\n\nBut also..."
               f"\n\nNever gonna give you up"
               f"\nNever gonna let you down"
               f"\nNever gonna run around and desert you"
               f"\nNever gonna make you cry"
               f"\nNever gonna say goodbye"
               f"\nNever gonna tell a lie and hurt you"
               f"\n\nWallet: {address[:5]}...{address[-4:]}\nX account: @{twitter_username}")
    signed_message = account.wallet.sign_message(message)
    async with authenticated_memeland(session, account) as memeland:
        response_json = await memeland.link_wallet(address, message, signed_message)
        status = response_json["status"]

        if status == "invalid_signature":
            logger.warning(f"{account} Неверная сигнатура")
            return

        if status == "reward_already_claimed":
            logger.warning(f"{account} Кошелек уже привязан")
            await _request_memeland_info(session, account)
            return

        if status == "success":
            logger.log(logging_level, f"{account} Кошелек успешно привязан")
            await _request_memeland_info(session, account)
            return

        logger.log(logging_level, f"{account} {status}")


@ensure_twitter_info
@filter_accounts(
    account_is_authed=False,
    twitter_statuses_blacklist=["BANNED", "LOCKED"],
    minimum_age=CONFIG.MINIMUM_ACCOUNT_AGE_IN_DAYS,
    minimum_followers_count=3,
)
async def auth_accounts(accounts: Iterable[Account]):
    await process_accounts_with_session(accounts, _auth_account)


@filter_accounts(account_is_authed=True)
@ensure_memeland_info
@filter_accounts(wallet_is_linked=False)
async def link_wallets(accounts: Iterable[Account]):
    await process_accounts_with_session(accounts, _link_wallet)
