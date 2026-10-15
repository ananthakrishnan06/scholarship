"""Explicit UTF-8 JSON for browser and Windows PowerShell clients."""

from rest_framework.renderers import JSONRenderer


class UTF8JSONRenderer(JSONRenderer):
    charset = "utf-8"
