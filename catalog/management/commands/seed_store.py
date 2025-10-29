from django.core.management.base import BaseCommand
from catalog.models import Category, Product, Variant


class Command(BaseCommand):
    help = "Seed initial categories and sample products for Rey&Hardy"

    def handle(self, *args, **options):
        tees, _ = Category.objects.get_or_create(name="T-shirts")
        oversize, _ = Category.objects.get_or_create(name="Oversized T-shirts")

        if not Product.objects.filter(name="Rey&Hardy Classic Tee").exists():
            p = Product.objects.create(
                name="Rey&Hardy Classic Tee",
                category=tees,
                description="Comfortable cotton tee with a perfect fit.",
                base_price=499,
                sale_price=449,
            )
            for size in ["M", "L", "XL", "XXL"]:
                for color in ["Red", "Black", "Navy Blue", "White", "Grey"]:
                    Variant.objects.get_or_create(product=p, size=size, color=color, sku=f"RHC-{size}-{color[:2].upper()}")

        self.stdout.write(self.style.SUCCESS("Seeded store data"))

