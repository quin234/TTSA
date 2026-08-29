
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsa_app', '0008_guestsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='multiplayergame',
            name='has_stockfish_opponent',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='multiplayergame',
            name='is_lobby_game',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name='multiplayergame',
            index=models.Index(fields=['is_lobby_game', 'status', 'time_control'], name='ttsa_app_mu_is_lobb_a9add8_idx'),
        ),
    ]
