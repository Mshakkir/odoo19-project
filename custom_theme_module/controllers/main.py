# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class WebsiteLanguage(Website):

    @http.route('/website/lang/<string:lang>', type='http', auth="public", website=True, sitemap=False)
    def change_lang(self, lang, r='/', **kwargs):
        """
        Change website language and redirect to the requested page

        :param lang: Language code (e.g., 'en_US', 'ar_SA')
        :param r: Redirect URL after language change
        """
        if lang == 'default':
            lang = request.website.default_lang_id.code

        # Get available languages for the website
        available_langs = request.website.language_ids.mapped('url_code')

        if lang in available_langs:
            # Set language in URL and context
            request.website = request.website.with_context(lang=lang)

            # Update language in session/cookie
            redirect = request.redirect(r or '/')
            redirect.set_cookie('frontend_lang', lang)

            return redirect

        # If language not available, redirect without changing
        return request.redirect(r or '/')

    @http.route('/website/get_current_language', type='json', auth='public', website=True)
    def get_current_language(self):
        """
        Get current language information (for AJAX requests if needed)
        """
        lang = request.env.context.get('lang', 'en_US')
        current_lang = request.env['res.lang']._lang_get(lang)

        return {
            'code': current_lang.code,
            'name': current_lang.name,
            'direction': current_lang.direction,
        }

    @http.route('/website/available_languages', type='json', auth='public', website=True)
    def available_languages(self):
        """
        Get all available languages for the current website
        """
        languages = []
        for lang in request.website.language_ids:
            languages.append({
                'code': lang.code,
                'url_code': lang.url_code,
                'name': lang.name,
                'direction': lang.direction,
            })
        return languages