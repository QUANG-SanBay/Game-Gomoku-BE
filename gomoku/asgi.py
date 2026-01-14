"""
ASGI config for gomoku project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.core.asgi import get_asgi_application
from matches.socketio_handler import sio
import socketio

# Tạo Django ASGI application
django_asgi_app = get_asgi_application()

# Kết hợp Socket.IO với Django
application = socketio.ASGIApp(
    sio,
    django_asgi_app,
    socketio_path='socket.io'
)
