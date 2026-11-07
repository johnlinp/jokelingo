from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('feed', '0006_post_short_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilteredAnalyticsEvent',
            fields=[],
            options={
                'verbose_name': 'Analytics event (excluding configured users)',
                'verbose_name_plural': 'Analytics events (excluding configured users)',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('feed.analyticsevent',),
        ),
    ]
