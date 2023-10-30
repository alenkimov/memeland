from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

import pyuseragents
from better_proxy import Proxy
from better_web3 import Wallet
from tinydb import TinyDB, Query


TwitterStatus = Literal["UNKNOWN", "BAD_TOKEN", "BANNED", "LOCKED", "GOOD"]


class Account:
    def __init__(
            self,
            wallet: Wallet,
            *,
            proxy: Proxy = None,
            number: int = None,
    ):
        self.wallet = wallet
        self.proxy = proxy
        self.number = number
        self.useragent = pyuseragents.random()
        self.auth_tokens: dict[str: str] = {}  # twitter, twitter_ct0, memeland
        self.memeland_info: dict | None = None
        self.tasks: dict | None = None
        self.twitter_info: dict | None = None
        self.twitter_status: TwitterStatus = "UNKNOWN"

    @property
    def short_twitter_auth_token(self) -> str:
        first_four = self.auth_tokens["twitter"][:4]
        last_four = self.auth_tokens["twitter"][-4:]
        return f"{first_four}...{last_four}"

    def __str__(self):
        additional_info = f'[{self.number:04}]' if self.number is not None else ''
        return f"{additional_info} [{self.short_twitter_auth_token}]"

    def save(self, db_path: str | Path):
        save_account(self, db_path)

    @property
    def points(self) -> int | None:
        if self.tasks:
            return self.tasks["points"]["current"]
        return None

    @property
    def twitter_account_age(self) -> int | None:
        if self.twitter_info:
            created_at_str = self.twitter_info['legacy']['created_at']
            created_at = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S +0000 %Y')
            return (datetime.utcnow() - created_at).days
        return None

    @property
    def followers_count(self) -> int | None:
        if self.twitter_info:
            return self.twitter_info['legacy']['followers_count']
        return None

    @property
    def wallet_is_linked(self) -> bool | None:
        if self.memeland_info:
            return bool(self.memeland_info["wallet"])
        return None


def save_account(account: Account, db_path: str | Path):
    db = TinyDB(db_path)
    DBAccount = Query()

    account_data = {
        'wallet': {
            'private_key': account.wallet.private_key,
            'address': account.wallet.address,
        },
        'auth_tokens': account.auth_tokens,
        'memeland_info': account.memeland_info,
        'memeland_tasks_info': account.tasks,
        'twitter_info': account.twitter_info,
        'twitter_status': account.twitter_status,
    }

    twitter_token = account.auth_tokens.get('twitter')
    if twitter_token is not None:
        existing_account = db.search(DBAccount['auth_tokens']['twitter'] == twitter_token)
        if existing_account:
            db.update(account_data, DBAccount['auth_tokens']['twitter'] == twitter_token)
        else:
            db.insert(account_data)
    else:
        print("Twitter token is not set. Account is not saved.")


def extract_or_create_accounts(
        twitter_auth_tokens: Iterable[str],
        db_path: str | Path,
) -> list[Account]:
    db = TinyDB(db_path)
    DBAccount = Query()

    accounts = []
    for i, token in enumerate(twitter_auth_tokens):
        account_data = db.get(DBAccount['auth_tokens']['twitter'] == token)
        wallet = Wallet.from_key(account_data['wallet']['private_key']) if account_data else Wallet.generate()
        account = Account(
            wallet=wallet,
            number=i
        )
        account.auth_tokens = account_data['auth_tokens'] if account_data else {'twitter': token}
        if account_data:
            account.memeland_info = account_data.get('memeland_info')
            account.tasks = account_data.get('memeland_tasks_info')
            account.twitter_info = account_data.get('twitter_info')
            account.twitter_status = account_data.get('twitter_status')
        accounts.append(account)

    return accounts
