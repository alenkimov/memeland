from typing import Iterable
from random import sample

import aiohttp

from bot.account import Account
from bot.auth import authenticated_twitter
from bot.process import process_accounts_with_session
from bot.config import CONFIG
from bot.filters import filter_accounts_by_twitter_info
from better_automation.utils.other import curry_async
from bot.logger import logger
from bot.update_info import update_twitter_info


async def _follow(
        session: aiohttp.ClientSession,
        account: Account,
        account_to: Account,
):
    async with authenticated_twitter(session, account) as twitter:
        await twitter.follow(account_to.twitter_info["rest_id"])
        logger.success(f"{account} Подписался на {account_to}")


async def print_followers_count(
        session: aiohttp.ClientSession,
        account: Account,
):
    async with authenticated_twitter(session, account) as twitter:
        await update_twitter_info(twitter, account, "DEBUG")
        logger.info(f"{account} Количество подписчиков теперь: {account.followers_count}")


@filter_accounts_by_twitter_info(minimum_age=CONFIG.MINIMUM_ACCOUNT_AGE_IN_DAYS)
async def follow_accounts(accounts: Iterable[Account]):
    accounts_to_print = []
    for account in accounts:
        follow_count = max(0, CONFIG.MINIMUM_FOLLOWERS_COUNT - account.followers_count)
        if follow_count:
            accounts_to_print.append(account)
        random_accounts = sample([a for a in accounts if a != account], k=follow_count)
        _follow_to_account = await curry_async(_follow)(account_to=account)
        await process_accounts_with_session(random_accounts, _follow_to_account)
    await process_accounts_with_session(accounts_to_print, print_followers_count)
