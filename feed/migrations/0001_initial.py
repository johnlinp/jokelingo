# Generated migration for Jokelingo database schema

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0001_initial'),
        ('auth', '0001_initial'),
    ]

    operations = [
        # Create User model (OAuth-only, password field exists but unused)
        # Using AbstractUser which provides: username, first_name, last_name, email, is_staff, is_active, date_joined, is_superuser
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=150)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.')),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'user',
            },
        ),
        # Add many-to-many relationships for groups and permissions (required by AbstractUser)
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(
                blank=True,
                help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                related_name='user_set',
                related_query_name='user',
                to='auth.group',
                verbose_name='groups',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(
                blank=True,
                help_text='Specific permissions for this user.',
                related_name='user_set',
                related_query_name='user',
                to='auth.permission',
                verbose_name='user permissions',
            ),
        ),
        # Create Post model
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('deleted', 'Deleted')], default='active', max_length=20)),
                ('source_language_code', models.CharField(max_length=10)),
                ('target_language_code', models.CharField(max_length=10)),
                ('source_provider', models.CharField(choices=[('reddit', 'Reddit'), ('instagram', 'Instagram'), ('twitter', 'Twitter')], max_length=20)),
                ('source_raw_url', models.TextField()),
                ('source_canonical_url', models.TextField()),
                ('translation_text', models.TextField(blank=True, null=True)),
                ('explanation_text', models.TextField(blank=True, null=True)),
                ('author_display_name_cache', models.CharField(blank=True, max_length=255, null=True)),
                ('helpful_count_cache', models.IntegerField(default=0)),
                ('confusing_count_cache', models.IntegerField(default=0)),
                ('author_user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='posts', to='feed.user')),
            ],
            options={
                'db_table': 'post',
            },
        ),
        # Create EngagementEvent model
        migrations.CreateModel(
            name='EngagementEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('engagement_type', models.CharField(choices=[('helpful', 'Helpful'), ('confusing', 'Confusing'), ('none', 'None')], default='none', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='engagement_events', to='feed.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='engagement_events', to='feed.user')),
            ],
            options={
                'db_table': 'engagement_event',
            },
        ),
        # Add EngagementEvent constraints and indexes
        migrations.AddConstraint(
            model_name='engagementevent',
            constraint=models.UniqueConstraint(fields=['post', 'user'], name='unique_post_user_engagement'),
        ),
        migrations.AddIndex(
            model_name='engagementevent',
            index=models.Index(fields=['post', 'user'], name='engagement_event_post_user_idx'),
        ),
    ]
