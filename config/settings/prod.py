import os

from .base import * # noqa: F403

DEBUG=False

ALLOWED_HOSTS = [h.strip() for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",") if h.strip()]