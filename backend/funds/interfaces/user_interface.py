from abc import ABC, abstractmethod

class UserInterface(ABC):
    @abstractmethod
    def get_investors(self):
        pass

    @abstractmethod
    def get_user_by_id(self, user_id):
        pass
