from django.core.management.base import BaseCommand, CommandError

from djangocms_supertext import conf
from djangocms_supertext.client import SupertextError


class Command(BaseCommand):
    help = "Checks the Supertext API key (cost-free)."

    def handle(self, *args, **options):
        settings = conf.load()
        if not settings.api_key:
            raise CommandError("No Supertext API key is configured. Set SUPERTEXT_API_KEY.")
        try:
            settings.client().validate_api_key()
        except SupertextError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Connected to {settings.base_url}. The API key works."))
