from app.core.base_dao import BaseDAO
from app.handlers.admin.models import Admin


class AdminDAO(BaseDAO[Admin]):
    model = Admin
