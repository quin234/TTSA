from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/multiplayer/(?P<game_code>[A-Z0-9]+)/$', consumers.MultiplayerGameConsumer.as_asgi()),
    re_path(r'ws/tournament/(?P<tournament_id>\d+)/standings/$', consumers.TournamentStandingsConsumer.as_asgi()),
    re_path(r'ws/admin/dashboard/$', consumers.AdminDashboardConsumer.as_asgi()),
]
