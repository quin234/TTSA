from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsa_app', '0003_multiplayergame_time_control_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='multiplayergame',
            name='color_preference',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
