from django.db import migrations
import uuid

def seed_portfolio_manager(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    
    Role.objects.get_or_create(
        name="PORTFOLIO_MANAGER",
        defaults={
            "id": uuid.uuid4(),
            "description": "Can modify real estate portfolio data",
            "is_system_role": True,
        },
    )

def unseed_portfolio_manager(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.filter(name="PORTFOLIO_MANAGER", is_system_role=True).delete()

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_alter_userroleassignment_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_portfolio_manager, reverse_code=unseed_portfolio_manager),
    ]
