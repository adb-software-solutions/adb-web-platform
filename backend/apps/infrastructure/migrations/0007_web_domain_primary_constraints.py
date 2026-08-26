from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("infrastructure", "0006_web_domain_specialists"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="dnszone",
            constraint=models.UniqueConstraint(
                fields=("domain",),
                condition=Q(is_primary=True),
                name="unique_primary_dns_zone",
            ),
        ),
        migrations.AddConstraint(
            model_name="tlscertificatedomain",
            constraint=models.UniqueConstraint(
                fields=("certificate",),
                condition=Q(is_primary=True),
                name="unique_primary_tls_domain",
            ),
        ),
    ]
