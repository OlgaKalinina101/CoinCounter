"""
Celery application configuration for coin_counter project.

This module initializes the Celery app and configures it to work with Django.
Tasks are automatically discovered from all installed apps.
"""
from __future__ import absolute_import

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coin_counter.settings")

app = Celery("coin_counter")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
