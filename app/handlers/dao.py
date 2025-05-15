from app.core.base_dao import BaseDAO
from app.handlers.models import Privacy_Policy


class PrivacyPolicyDAO(BaseDAO[Privacy_Policy]):
    model = Privacy_Policy
