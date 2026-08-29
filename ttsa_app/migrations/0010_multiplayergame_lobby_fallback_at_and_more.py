
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsa_app', '0009_multiplayergame_has_stockfish_opponent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='multiplayergame',
            name='lobby_fallback_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddIndex(
            model_name='multiplayergame',
            index=models.Index(fields=['is_lobby_game', 'status', 'lobby_fallback_at'], name='ttsa_app_mu_is_lobb_9990d5_idx'),
        ),
    ]
