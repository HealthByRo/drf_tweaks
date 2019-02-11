from django.conf import settings

URL_PARSER = getattr(settings, 'DRF_TWEAKS_PARSER_CLASS', 'drf_tweaks.parsers.UnderlineQueryParamParser')
