# Generated migration to add imgur as a source provider option

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0002_analytics_event'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='source_provider',
            field=models.CharField(
                choices=[
                    ('reddit', 'Reddit'),
                    ('instagram', 'Instagram'),
                    ('twitter', 'Twitter'),
                    ('imgur', 'Imgur')
                ],
                max_length=20
            ),
        ),
    ]
