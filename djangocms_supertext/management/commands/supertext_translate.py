from django.core.management.base import BaseCommand, CommandError

from djangocms_supertext import translator
from djangocms_supertext.client import SupertextError


class Command(BaseCommand):
    help = "Translates a django CMS page with Supertext: supertext_translate <page id> --from en [--to de fr] [--overwrite]"

    def add_arguments(self, parser):
        parser.add_argument("page", type=int, help="Page id")
        parser.add_argument("--from", dest="source", required=True, help="Source language code")
        parser.add_argument("--to", dest="targets", nargs="*", help="Target language codes (default: all other languages of the site)")
        parser.add_argument("--overwrite", action="store_true", help="Replace languages that already exist")

    def handle(self, *args, **options):
        from cms.models import Page

        page = Page.objects.filter(pk=options["page"]).first()
        if page is None:
            raise CommandError(f"Page {options['page']} not found.")
        targets = options["targets"] or [lang["code"] for lang in translator.site_languages(page) if lang["code"] != options["source"]]
        try:
            results = translator.translate_page(page, options["source"], targets, overwrite=options["overwrite"])
        except SupertextError as error:
            raise CommandError(str(error)) from error
        failed = False
        for result in results:
            line = f"{result.language}: {result.status}" + (f" ({result.message})" if result.message else "")
            failed = failed or result.status == "error"
            self.stdout.write(self.style.ERROR(line) if result.status == "error" else self.style.SUCCESS(line))
        if failed:
            raise CommandError("Some languages failed.")
