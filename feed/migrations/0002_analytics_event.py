# Generated migration for AnalyticsEvent model

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalyticsEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('engagement_click_anon', 'Engagement Click (Anonymous)'), ('login_click_topright_anon', 'Login Click Top-Right (Anonymous)'), ('load_more_click', 'Load More Click')], db_index=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='analytics_events', to='feed.user')),
            ],
            options={
                'db_table': 'analytics_event',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['event_type', '-created_at'], name='analytics_event_event_type_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsevent',
            index=models.Index(fields=['user', '-created_at'], name='analytics_event_user_created_at_idx'),
        ),
    ]
