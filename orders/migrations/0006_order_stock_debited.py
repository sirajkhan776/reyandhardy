from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_item_cost_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stock_debited",
            field=models.BooleanField(default=False),
        ),
    ]

