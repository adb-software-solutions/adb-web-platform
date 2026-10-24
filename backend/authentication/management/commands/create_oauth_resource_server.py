from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from authentication.oauth.models import OAuthResourceServer
from authentication.oauth.services import create_resource_server, generate_secret, hash_secret


class Command(BaseCommand):
    help = (
        "Register a service that accepts OAuth access tokens and print its introspection "
        "credentials. The secret is shown only once."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Display name shown on the consent screen.")
        parser.add_argument(
            "resource", help="Canonical resource URI, e.g. https://brain.example.com/mcp"
        )
        parser.add_argument(
            "--scope",
            action="append",
            dest="scopes",
            help="Scope the resource accepts. Repeat for several. Defaults to 'mcp'.",
        )
        parser.add_argument(
            "--rotate-secret",
            action="store_true",
            help="Issue a new introspection secret for an existing resource server.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        resource = options["resource"].rstrip("/")
        existing = OAuthResourceServer.objects.filter(resource=resource).first()

        if existing is not None:
            if not options["rotate_secret"]:
                raise CommandError(
                    f"{resource} is already registered. Use --rotate-secret to replace its secret."
                )
            secret = generate_secret()
            existing.introspection_secret_hash = hash_secret(secret)
            existing.save(update_fields=["introspection_secret_hash"])
            server = existing
        else:
            server, secret = create_resource_server(options["name"], resource, options["scopes"])

        self.stdout.write(self.style.SUCCESS(f"Resource server: {server.name} ({server.resource})"))
        self.stdout.write(f"OAUTH_INTROSPECTION_CLIENT_ID={server.id}")
        self.stdout.write(f"OAUTH_INTROSPECTION_CLIENT_SECRET={secret}")
