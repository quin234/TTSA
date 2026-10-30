# Generated manually to add missing rating_deviation and volatility fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsaadmin', '0013_add_rating_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentplayer',
            name='rating_deviation',
            field=models.FloatField(default=350.0),
        ),
        migrations.AddField(
            model_name='tournamentplayer',
            name='volatility',
            field=models.FloatField(default=0.06),
        ),
    ]
