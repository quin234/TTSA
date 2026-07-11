from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/multiplayer/(?P<game_code>[A-Z0-9]+)/$', consumers.MultiplayerGameConsumer.as_asgi()),
]
