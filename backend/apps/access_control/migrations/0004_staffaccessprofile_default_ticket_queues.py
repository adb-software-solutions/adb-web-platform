from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("access_control", "0003_alter_staffaccessprofile_all_ticket_queues"),
        ("ticketing", "0005_vendor_routing"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffaccessprofile",
            name="default_ticket_queues",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Queues shown in the staff user's default ticket work queue. "
                    "No explicit selection means every accessible enabled queue."
                ),
                related_name="default_for_staff_profiles",
                to="ticketing.ticketqueue",
            ),
        ),
    ]
