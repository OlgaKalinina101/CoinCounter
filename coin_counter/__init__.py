"""
Main package initialization for coin_counter project.

Imports Celery app to ensure it's loaded when Django starts.
"""
from __future__ import absolute_import

from .celery import app as celery_app

__all__ = ("celery_app",)