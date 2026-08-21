import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",") if h.strip()]

# Vercel terminates TLS at the edge and forwards the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# This service sends no email. The default MAILERS entry uses the console backend,
# which --deploy flags as production-unsafe; silenced rather than configuring SMTP
# for a feature the API does not have.
SILENCED_SYSTEM_CHECKS = ["mail.E001"]
