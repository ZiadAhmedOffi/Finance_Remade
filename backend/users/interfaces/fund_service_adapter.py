from users.interfaces.fund_interface import FundInterface
from funds.models import Fund, FundLog

class FundServiceAdapter(FundInterface):
    def create_fund_log(self, actor, target_fund, action, metadata=None):
        return FundLog.objects.create(
            actor=actor,
            target_fund=target_fund,
            action=action,
            metadata=metadata or {}
        )

    def get_fund_by_id(self, fund_id):
        try:
            return Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            return None
