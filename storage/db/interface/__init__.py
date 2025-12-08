from config import settings

from .base import BaseInterface
from .interfaces.user import UsersDBInterface


class DBInterface(BaseInterface):
    def __init__(self, db_url: str):
        super().__init__(db_url)
        self.users = UsersDBInterface(session_=self.async_ses)


db = DBInterface(settings.DB_URL)
