from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/multiplayer/(?P<game_id>\d+)/$', consumers.MultiplayerGameConsumer.as_asgi()),
]
