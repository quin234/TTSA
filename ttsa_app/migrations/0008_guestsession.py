import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsa_app', '0007_alter_playerprofile_last_played_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GuestSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_digest', models.CharField(db_index=True, max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=24)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='guest_session', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['expires_at', '-created_at'], name='ttsa_app_gu_expires_aefdef_idx')],
            },
        ),
    ]
