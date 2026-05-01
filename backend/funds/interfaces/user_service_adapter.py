from funds.interfaces.user_interface import UserInterface
from users.models import UserRoleAssignment, User

class UserServiceAdapter(UserInterface):
    def get_investors(self):
        # This will be refactored to use user_selectors later
        return User.objects.filter(
            role_assignments__role__name="INVESTOR"
        ).distinct()

    def get_user_by_id(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
