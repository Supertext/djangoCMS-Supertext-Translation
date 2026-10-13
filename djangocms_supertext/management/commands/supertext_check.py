from django.core.management.base import BaseCommand, CommandError

from djangocms_supertext import conf, reporting


class Command(BaseCommand):
    help = "Checks the Supertext API key (cost-free) and sends a version report (unless version reports are off)."

    def handle(self, *args, **options):
        settings = conf.load()
        # The SDK's key check, stored like Test connection; then a "check" report to the Commando Center.
        result = reporting.run("test_connection", settings)
        check = result.check if result else settings.client().check_api_key()
        if settings.reports_enabled:
            sent = reporting.run("report_check", settings)
            self.stdout.write(f"Version report to Supertext: {'sent' if sent and sent.sent else 'not sent'}.")
        else:
            self.stdout.write("Version report to Supertext: off.")
        if check.status == "missing":
            raise CommandError(
                "No Supertext API key is configured. Set SUPERTEXT_API_KEY.\n"
                f"No Supertext account yet? Create one at {conf.SIGNUP_URL}\n"
                f"Generate your API key at {conf.API_KEY_URL} (supertext.com → Integrations → API; requires the Admin role)."
            )
        if check.status == "invalid":
            raise CommandError(
                f"Supertext rejected the API key (HTTP {check.http_status}). Check that you copied the whole key, "
                f"or generate a new one at {conf.API_KEY_URL} (requires the Admin role).\n"
                f"No Supertext account yet? Create one at {conf.SIGNUP_URL}"
            )
        if check.status == "unreachable":
            raise CommandError(f"The API key couldn't be checked because Supertext can't be reached ({settings.base_url}).")
        if check.status != "ok":
            raise CommandError(f"The API key couldn't be checked: Supertext answered with an error ({check.http_status or check.error_code}).")
        self.stdout.write(self.style.SUCCESS(f"Connected to {settings.base_url}. The API key works. Plugin version {reporting.__version__}."))
