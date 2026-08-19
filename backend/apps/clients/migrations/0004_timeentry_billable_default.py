from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0003_time_tracking_contexts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timeentry",
            name="billable",
            field=models.BooleanField(default=False),
        ),
    ]
