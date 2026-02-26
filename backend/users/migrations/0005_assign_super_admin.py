from django.db import migrations
import uuid


def assign_super_admin(apps, schema_editor):
    User = apps.get_model("users", "User")
    Role = apps.get_model("users", "Role")
    UserRoleAssignment = apps.get_model("users", "UserRoleAssignment")

    try:
        user = User.objects.get(email="admin@example.com")
    except User.DoesNotExist:
        return  # Fail silently if user does not exist

    try:
        role = Role.objects.get(name="SUPER_ADMIN")
    except Role.DoesNotExist:
        return  # Fail silently if role missing

    # Activate the admin user
    user.status = "ACTIVE"
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()

    # Assign role globally (fund=None)
    UserRoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        fund=None,
        defaults={
            "id": uuid.uuid4(),
            "assigned_by": user,  # self-assigned during seed
        },
    )


def unassign_super_admin(apps, schema_editor):
    User = apps.get_model("users", "User")
    Role = apps.get_model("users", "Role")
    UserRoleAssignment = apps.get_model("users", "UserRoleAssignment")

    try:
        user = User.objects.get(email="admin@example.com")
        role = Role.objects.get(name="SUPER_ADMIN")
    except (User.DoesNotExist, Role.DoesNotExist):
        return

    UserRoleAssignment.objects.filter(
        user=user,
        role=role,
        fund=None,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_role_initial_data"),
    ]

    operations = [
        migrations.RunPython(assign_super_admin, reverse_code=unassign_super_admin),
    ]