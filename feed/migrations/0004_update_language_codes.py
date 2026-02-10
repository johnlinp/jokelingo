# Generated migration to update language codes from en_US/es_ES to en/es

from django.db import migrations


def update_language_codes(apps, schema_editor):
    """Update existing language codes from en_US/es_ES to en/es."""
    Post = apps.get_model('feed', 'Post')
    
    # Update en_US to en
    Post.objects.filter(target_language_code='en_US').update(target_language_code='en')
    Post.objects.filter(source_language_code='en_US').update(source_language_code='en')
    
    # Update es_ES to es
    Post.objects.filter(target_language_code='es_ES').update(target_language_code='es')
    Post.objects.filter(source_language_code='es_ES').update(source_language_code='es')


def reverse_language_codes(apps, schema_editor):
    """Reverse migration: update en/es back to en_US/es_ES."""
    Post = apps.get_model('feed', 'Post')
    
    # Update en back to en_US
    Post.objects.filter(target_language_code='en').update(target_language_code='en_US')
    Post.objects.filter(source_language_code='en').update(source_language_code='en_US')
    
    # Update es back to es_ES
    Post.objects.filter(target_language_code='es').update(target_language_code='es_ES')
    Post.objects.filter(source_language_code='es').update(source_language_code='es_ES')


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0003_add_imgur_source_provider'),
    ]

    operations = [
        migrations.RunPython(update_language_codes, reverse_language_codes),
    ]
