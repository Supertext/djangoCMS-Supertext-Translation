"""Adds "Translate with Supertext…" to the django CMS toolbar's Language menu (edit mode)."""

from cms.cms_toolbars import LANGUAGE_MENU_IDENTIFIER
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils import page_permissions
from django.utils.translation import gettext_lazy as _

from .admin import PERMISSION, translate_url


@toolbar_pool.register
class SupertextToolbar(CMSToolbar):
    def post_template_populate(self):
        page = getattr(self.request, "current_page", None)
        if not page or not self.toolbar.edit_mode_active or not self.request.user.has_perm(PERMISSION):
            return
        if not page_permissions.user_can_change_page(user=self.request.user, page=page, site=self.current_site):
            return
        menu = self.toolbar.get_or_create_menu(LANGUAGE_MENU_IDENTIFIER, _("Language"), position=-1)
        menu.add_break("supertext-break")
        menu.add_modal_item(_("Translate with Supertext"), url=translate_url(page, self.current_lang))
