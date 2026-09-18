from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curation", "0011_bookmark_like_resource_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourcecontent",
            name="version_label",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
