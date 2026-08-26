from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import Q


def demote_duplicate_primaries(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    database = schema_editor.connection.alias
    DNSZone = apps.get_model("infrastructure", "DNSZone")
    TLSCertificateDomain = apps.get_model("infrastructure", "TLSCertificateDomain")

    seen_domains = set()
    for zone in DNSZone.objects.using(database).filter(is_primary=True).order_by("domain_id", "id"):
        if zone.domain_id in seen_domains:
            zone.is_primary = False
            zone.save(update_fields=["is_primary"], using=database)
        else:
            seen_domains.add(zone.domain_id)

    seen_certificates = set()
    primary_links = (
        TLSCertificateDomain.objects.using(database)
        .filter(is_primary=True)
        .order_by("certificate_id", "id")
    )
    for link in primary_links:
        if link.certificate_id in seen_certificates:
            link.is_primary = False
            link.save(update_fields=["is_primary"], using=database)
        else:
            seen_certificates.add(link.certificate_id)


class Migration(migrations.Migration):
    dependencies = [
        ("infrastructure", "0006_web_domain_specialists"),
    ]

    operations = [
        migrations.RunPython(demote_duplicate_primaries, migrations.RunPython.noop),
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
