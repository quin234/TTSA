from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsa_app', '0002_playerplusapplication'),
    ]

    operations = [
        migrations.AlterField(
            model_name='multiplayergame',
            name='game_type',
            field=models.CharField(choices=[('standard', 'Standard Chess'), ('bullet', 'Bullet (2+1)'), ('blitz', 'Blitz (5+0)'), ('rapid', 'Rapid (10+0)'), ('classical', 'Classical (30+0)')], default='standard', max_length=20),
        ),
        migrations.AddField(
            model_name='multiplayergame',
            name='increment_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='multiplayergame',
            name='initial_time',
            field=models.PositiveIntegerField(default=600),
        ),
        migrations.AddField(
            model_name='multiplayergame',
            name='time_control',
            field=models.CharField(default='10+0', max_length=10),
        ),
    ]
