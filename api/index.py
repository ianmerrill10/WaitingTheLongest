"""Vercel Serverless Function entrypoint.

Vercel's Python runtime expects a WSGI callable.
FastAPI is ASGI, so we adapt it via asgi2wsgi.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from a2wsgi import ASGIMiddleware

from backend.app.main import app as asgi_app

app = ASGIMiddleware(asgi_app)
