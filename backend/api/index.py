"""Vercel serverless entrypoint for the Django backend.

Vercel's Python runtime serves the module-level ``app`` (a WSGI callable).
Used only when deploying the backend to Vercel (Root Directory = ``backend``);
Render keeps using gunicorn against ``config.wsgi`` and ignores this file.
"""

import os
import sys

# Ensure the backend root (parent of this api/ dir) is importable, so that
# `config` and `trips` resolve no matter what cwd Vercel runs the function in.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402

app = application
