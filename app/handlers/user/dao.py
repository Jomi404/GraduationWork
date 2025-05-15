from app.core.base_dao import BaseDAO
from app.handlers.user.models import Agree_Policy


class AgreePolicyDAO(BaseDAO[Agree_Policy]):
    model = Agree_Policy

