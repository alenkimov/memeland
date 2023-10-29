from typing import Iterable

import aiohttp

from bot.account import Account
from bot.api import MemelandAPI
from bot.auth import authenticated_memeland, authenticated_twitter, auth_memeland
from bot.process import process_accounts_with_session
from bot.logger import logger, LoggingLevel
from bot.config import CONFIG
from bot.filters import (
    filter_accounts_by_twitter_info,
    filter_accounts_by_memeland_info,
    filter_accounts_by_token,
)
from bot.update_info import update_memeland_info


async def _auth_account(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "SUCCESS",
):
    async with authenticated_twitter(session, account) as twitter:
        memeland = await auth_memeland(session, twitter, account, logging_level)
        await update_memeland_info(memeland, account)


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
            await update_memeland_info(memeland, account)
            return

        if status == "success":
            logger.log(logging_level, f"{account} Кошелек успешно привязан")
            await update_memeland_info(memeland, account)
            return

        logger.log(logging_level, f"{account} {status}")


@filter_accounts_by_token("memeland", presence=False)
@filter_accounts_by_twitter_info(
    minimum_age=CONFIG.MINIMUM_ACCOUNT_AGE_IN_DAYS,
    minimum_followers_count=3,
)
async def auth_accounts(accounts: Iterable[Account]):
    await process_accounts_with_session(accounts, _auth_account)


@filter_accounts_by_token("memeland", presence=True)
@filter_accounts_by_memeland_info(wallet_is_linked=False)
async def link_wallets(accounts: Iterable[Account]):
    await process_accounts_with_session(accounts, _link_wallet)


async def _perform_task(
        memeland: MemelandAPI,
        account: Account,
        task_id: str,
        endpoint: str,
        payload: dict = None,
) -> None:
    response_json = await memeland.perform_task(endpoint, payload=payload)
    status = response_json["status"]
    if status == "success":
        logger.success(f"{account} Успешно выполнил таск {task_id}")
    else:
        logger.warning(f"{account} Не удалось выполнить таск {task_id}: {status}")


async def _complete_tasks(
        session: aiohttp.ClientSession,
        account: Account,
):
    async with authenticated_memeland(session, account) as memeland:
        for task in account.tasks["tasks"] + account.tasks["timely"]:
            is_completed: bool = task["completed"]
            task_id: str = task["id"]

            if not is_completed:
                if task_id.startswith("follow"):
                    payload = {'followId': task_id}
                    await _perform_task(memeland, account, task_id, "twitter-follow", payload)
                elif task_id == "goingToBinance":
                    await _perform_task(memeland, account, task_id, "daily-task/goingToBinance")
                elif task_id == "shareMessage":
                    await _perform_task(memeland, account, task_id, "share-message")
                elif task_id == "inviteCode" and CONFIG.NFT:
                    payload = {'code': CONFIG.NFT}
                    await _perform_task(memeland, account, task_id, "invite-code", payload)
                elif task_id == "twitterName" and "❤️ Memecoin" in account.memeland_info["twitter"]["username"]:
                    await _perform_task(memeland, account, task_id, "twitter-name")

        await update_memeland_info(memeland, account)


@filter_accounts_by_token("memeland", presence=True)
@filter_accounts_by_memeland_info(wallet_is_linked=True)
async def complete_tasks(accounts: Iterable[Account]):
    await process_accounts_with_session(accounts, _complete_tasks)
