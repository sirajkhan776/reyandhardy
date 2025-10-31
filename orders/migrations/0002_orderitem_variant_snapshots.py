from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="variant_size",
            field=models.CharField(max_length=10, blank=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="variant_color",
            field=models.CharField(max_length=30, blank=True),
        ),
    ]

