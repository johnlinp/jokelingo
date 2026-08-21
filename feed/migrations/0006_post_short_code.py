import secrets

from django.db import migrations, models


SHORT_CODE_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'
SHORT_CODE_LENGTH = 8


def generate_short_code():
    return ''.join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))


def populate_short_codes(apps, schema_editor):
    Post = apps.get_model('feed', 'Post')

    for post in Post.objects.filter(short_code__isnull=True).iterator():
        short_code = generate_short_code()
        while Post.objects.filter(short_code=short_code).exists():
            short_code = generate_short_code()
        post.short_code = short_code
        post.save(update_fields=['short_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0005_analyticsevent_client_country_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='short_code',
            field=models.CharField(editable=False, max_length=SHORT_CODE_LENGTH, null=True, unique=True),
        ),
        migrations.RunPython(populate_short_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='post',
            name='short_code',
            field=models.CharField(editable=False, max_length=SHORT_CODE_LENGTH, unique=True),
        ),
    ]
