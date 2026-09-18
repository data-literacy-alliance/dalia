# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curation", "0005_resourcecontent_search_vector_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="sync_name_from_provider",
            field=models.BooleanField(
                default=True,
                help_text="Automatically update given and family name from the login provider on each login",
            ),
        ),
    ]
