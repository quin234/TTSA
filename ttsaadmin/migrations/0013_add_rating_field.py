# Generated manually to add missing rating field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsaadmin', '0012_add_sent_by_to_smsmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentplayer',
            name='rating',
            field=models.PositiveIntegerField(db_index=True, default=1500),
        ),
    ]
