from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from authentication.oauth.models import OAuthClient
from authentication.oauth.services import OAuthError, create_confidential_client


class Command(BaseCommand):
    help = (
        "Create a pre-registered confidential OAuth client, such as a server-rendered "
        "frontend, and print its credentials. The secret is shown only once."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Display name shown on the consent screen.")
        parser.add_argument(
            "--redirect-uri",
            action="append",
            dest="redirect_uris",
            required=True,
            help="Allowed redirect URI. Repeat for several.",
        )
        parser.add_argument(
            "--auth-method",
            choices=[OAuthClient.AUTH_METHOD_SECRET_BASIC, OAuthClient.AUTH_METHOD_SECRET_POST],
            default=OAuthClient.AUTH_METHOD_SECRET_BASIC,
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            client, secret = create_confidential_client(
                options["name"],
                options["redirect_uris"],
                options["auth_method"],
            )
        except OAuthError as exc:
            raise CommandError(exc.description) from exc

        self.stdout.write(self.style.SUCCESS(f"OAuth client: {client.client_name}"))
        self.stdout.write(f"OAUTH_CLIENT_ID={client.client_id}")
        self.stdout.write(f"OAUTH_CLIENT_SECRET={secret}")
