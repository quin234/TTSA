from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ttsaadmin', '0003_academysettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='completed_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
