from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0004_update_language_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='analyticsevent',
            name='client_country_code',
            field=models.CharField(blank=True, db_index=True, max_length=10, null=True),
        ),
    ]
