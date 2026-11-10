from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_advance_transaction"),
        ("residents", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="resident",
            name="advance_balance",
        ),
    ]