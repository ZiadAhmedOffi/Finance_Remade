from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

def rename_columns_if_exists(apps, schema_editor):
    from django.db import connection
    cursor = connection.cursor()
    
    # Check existing columns
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'funds_investoraction'")
    columns = [row[0] for row in cursor.fetchall()]
    
    # Use schema_editor to rename if possible, or raw SQL
    if 'seller_id' in columns and 'investor_selling_id' not in columns:
        cursor.execute("ALTER TABLE funds_investoraction RENAME COLUMN seller_id TO investor_selling_id")
    
    if 'buyer_id' in columns and 'investor_sold_to_id' not in columns:
        cursor.execute("ALTER TABLE funds_investoraction RENAME COLUMN buyer_id TO investor_sold_to_id")
        
    if 'units_involved' in columns and 'units' not in columns:
        cursor.execute("ALTER TABLE funds_investoraction RENAME COLUMN units_involved TO units")

class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0015_fund_total_units_investoraction_discount_percentage_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(rename_columns_if_exists),
        migrations.AddField(
            model_name='investoraction',
            name='original_value',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=30, null=True),
        ),
        migrations.AddField(
            model_name='investoraction',
            name='exit_value',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=30, null=True),
        ),
    ]
