from users.models import User, Role

def get_active_users():
    return User.objects.filter(status="ACTIVE", is_deleted=False).order_by("email")

def get_pending_users():
    return User.objects.filter(status="PENDING", is_deleted=False).order_by("-date_joined")

def get_user_by_id(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

def get_all_roles():
    return Role.objects.all()
