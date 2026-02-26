# users/migrations/000X_seed_roles.py

from django.db import migrations
import uuid


def seed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")

    system_roles = [
        {
            "name": "SUPER_ADMIN",
            "description": "Full system access",
        },
        {
            "name": "ACCESS_MANAGER",
            "description": "Manages user approvals and roles",
        },
        {
            "name": "STEERING_COMMITTEE",
            "description": "Can modify fund data",
        },
        {
            "name": "INVESTOR",
            "description": "View-only access to assigned funds",
        },
    ]

    for role_data in system_roles:
        Role.objects.get_or_create(
            name=role_data["name"],
            defaults={
                "id": uuid.uuid4(),
                "description": role_data["description"],
                "is_system_role": True,
            },
        )


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")

    Role.objects.filter(
        name__in=[
            "SUPER_ADMIN",
            "ACCESS_MANAGER",
            "STEERING_COMMITTEE",
            "INVESTOR",
        ],
        is_system_role=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_company_user_job_title_user_phone_number"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_code=unseed_roles),
    ]