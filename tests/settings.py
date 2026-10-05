SECRET_KEY = "tests"
DEBUG = False
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "djangocms_supertext",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "cms",
    "menus",
    "treebeard",
    "sekizai",
    "djangocms_text",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
]
ROOT_URLCONF = "tests.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": ["tests/templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.template.context_processors.i18n",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "sekizai.context_processors.sekizai",
        "cms.context_processors.cms_settings",
    ]},
}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("de-ch", "Deutsch (Schweiz)"), ("fr-ch", "Français (Suisse)")]
SITE_ID = 1
CMS_CONFIRM_VERSION4 = True
CMS_PERMISSION = False
CMS_TEMPLATES = [("page.html", "Page")]
CMS_LANGUAGES = {1: [{"code": c, "name": n, "public": True} for c, n in LANGUAGES]}
STATIC_URL = "/static/"
SUPERTEXT = {"API_KEY": "test-key", "API_URL": "https://api.test/v1/", "LANGUAGES": {"de-ch": {"politeness": "more"}}, "POLL_INTERVAL": 0}
SILENCED_SYSTEM_CHECKS = ["treebeard.E001"]
