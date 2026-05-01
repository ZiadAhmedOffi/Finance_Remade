from abc import ABC, abstractmethod

class FundInterface(ABC):
    @abstractmethod
    def create_fund_log(self, actor, target_fund, action, metadata=None):
        pass

    @abstractmethod
    def get_fund_by_id(self, fund_id):
        pass
