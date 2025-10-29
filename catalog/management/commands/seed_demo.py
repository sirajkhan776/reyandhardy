import io
import random
from decimal import Decimal
from typing import List

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from PIL import Image, ImageDraw, ImageFont

from catalog.models import Category, Product, Variant, ProductImage
from coupons.models import Coupon
from reviews.models import Review
from core.models import Banner


class Command(BaseCommand):
    help = "Seed demo data: categories, products (with variants, images), coupons, users, reviews"

    sizes = ["M", "L", "XL", "XXL"]
    colors = ["Red", "Black", "Navy Blue", "White", "Grey"]

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data…")
        self.seed_categories()
        products = self.seed_products()
        self.seed_coupons()
        users = self.seed_users()
        self.seed_reviews(users, products)
        self.seed_banners(products)
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def seed_categories(self):
        for name in ["T-shirts", "Oversized T-shirts"]:
            Category.objects.get_or_create(name=name)

    def seed_products(self) -> List[Product]:
        tees = Category.objects.get(name="T-shirts")
        oversize = Category.objects.get(name="Oversized T-shirts")

        catalogue = [
            ("Classic Cotton Tee", tees, 499, 449, "100% cotton. Breathable everyday T‑shirt."),
            ("Graphic Street Tee", tees, 599, 499, "Soft cotton with bold front graphic. Street style."),
            ("Essential Pocket Tee", tees, 549, None, "Minimal tee with chest pocket. Everyday essential."),
            ("Oversized Drop Shoulder", oversize, 699, 599, "Relaxed fit, drop shoulder oversized tee."),
            ("Oversized Heavyweight", oversize, 799, 699, "Heavyweight fabric for premium drape."),
            ("Oversized Retro Print", oversize, 749, 649, "Retro inspired print, soft hand‑feel."),
        ]

        products: List[Product] = []
        for name, cat, base, sale, desc in catalogue:
            slug = slugify(f"reyhardy-{name}")
            p, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": f"Rey&Hardy {name}",
                    "category": cat,
                    "description": self._description_block(desc),
                    "base_price": Decimal(str(base)),
                    "sale_price": Decimal(str(sale)) if sale else None,
                    "is_active": True,
                },
            )
            # Ensure all variants exist even on re-seed
            for size in self.sizes:
                for color in self.colors:
                    Variant.objects.get_or_create(
                        product=p,
                        size=size,
                        color=color,
                        defaults={
                            "sku": self._sku_for(p, size, color),
                            "stock": random.randint(10, 80),
                        },
                    )
            # Generated images per color
            self._ensure_images(p)
            products.append(p)
        return products

    def _sku_for(self, product: Product, size: str, color: str) -> str:
        # Use product ID and short slug to guarantee uniqueness across products
        base = f"RH{product.id}-{slugify(product.name)[:6].upper()}"
        return f"{base}-{size}-{color[:2].upper()}"

    def _description_block(self, blurb: str) -> str:
        return (
            f"{blurb}\n\n"
            "Details:\n"
            "- Fabric: 100% Cotton\n"
            "- Fit: Regular / Oversized\n"
            "- Care: Machine wash cold, dry in shade\n"
            "- Made in India\n"
        )

    def _ensure_images(self, product: Product):
        """Generate a colored T‑shirt render per color if not present."""
        base_bg = (248, 250, 252)
        # Make newly generated first color the primary image
        if product.images.exists():
            product.images.update(is_primary=False)
        for idx, color_name in enumerate(self.colors):
            # Skip if an image containing this color already exists
            if product.images.filter(alt_text__icontains=color_name).exists():
                continue
            img = Image.new("RGB", (900, 900), color=base_bg)
            draw = ImageDraw.Draw(img)

            # Title text
            try:
                font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
            except Exception:
                font_title = ImageFont.load_default()

            title = product.name
            try:
                left, top, right, bottom = draw.textbbox((0, 0), title, font=font_title)
                tw, th = right - left, bottom - top
            except Exception:
                try:
                    tw, th = font_title.getsize(title)
                except Exception:
                    tw, th = (400, 60)
            draw.rectangle([(60, 60), (840, 840)], outline=(226, 232, 240), width=4)
            draw.text(((900 - tw) / 2, 820 - th), title, fill=(17, 24, 39), font=font_title)

            # Draw T‑shirt silhouette
            fill = self._color_rgb(color_name)
            outline = (30, 41, 59)
            self._draw_tshirt(draw, fill, outline)

            # Neck hole
            neck_w, neck_h = 150, 90
            cx, cy = 450, 235
            draw.ellipse([(cx - neck_w // 2, cy - neck_h // 2), (cx + neck_w // 2, cy + neck_h // 2)], fill=base_bg)

            # Save
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=88)
            buf.seek(0)
            filename = f"{product.slug}-{slugify(color_name)}.jpg"
            ProductImage.objects.create(
                product=product,
                image=ContentFile(buf.read(), name=filename),
                alt_text=f"{product.name} - {color_name}",
                is_primary=(idx == 0),
            )

    def seed_coupons(self):
        coupons = [
            ("WELCOME10", "10% off for new users", 10),
            ("FESTIVE20", "Festive sale 20% off", 20),
            ("CLEARANCE25", "Clearance 25% off", 25),
        ]
        for code, desc, pct in coupons:
            Coupon.objects.get_or_create(code=code, defaults={"description": desc, "discount_percent": pct, "active": True})

    def seed_users(self):
        User = get_user_model()
        users = []
        dataset = [
            ("alice", "alice@example.com"),
            ("bob", "bob@example.com"),
            ("charlie", "charlie@example.com"),
        ]
        for username, email in dataset:
            u, _ = User.objects.get_or_create(username=username, defaults={"email": email})
            if not u.has_usable_password():
                u.set_password("password123")
                u.save()
            users.append(u)
        return users

    def seed_reviews(self, users, products: List[Product]):
        texts = [
            "Great fabric and fit. Will buy again!",
            "Quality is top notch, loved the print.",
            "Comfortable and looks premium.",
            "Nice oversized look, perfect for casual wear.",
        ]
        for p in products:
            for u in users:
                rating = random.choice([4, 5])
                title = random.choice(["Awesome Tee", "Loved it", "Great Quality", "Premium feel"]) 
                body = random.choice(texts)
                Review.objects.get_or_create(product=p, user=u, defaults={"rating": rating, "title": title, "body": body})

    def seed_banners(self, products: List[Product]):
        if Banner.objects.exists():
            return
        # Create 3 banners using existing product images if available
        picks = products[:3]
        order = 0
        for p in picks:
            order += 1
            img = p.images.first()
            if not img:
                continue
            Banner.objects.create(
                title=p.name,
                subtitle="New arrivals • Limited time pricing",
                image=img.image,
                link_url=f"/product/{p.slug}/",
                button_text="Shop now",
                sort_order=order,
                is_active=True,
            )

    def _color_rgb(self, name: str):
        mapping = {
            "Red": (239, 68, 68),
            "Black": (17, 24, 39),
            "Navy Blue": (30, 58, 138),
            "White": (245, 247, 250),
            "Grey": (107, 114, 128),
        }
        return mapping.get(name, (99, 102, 241))

    def _draw_tshirt(self, draw: ImageDraw.ImageDraw, fill, outline):
        """Draw a simple T‑shirt polygon silhouette on a 900x900 canvas."""
        # Approximate T‑shirt silhouette
        points = [
            (360, 220), (520, 220),  # shoulder line
            (750, 220), (840, 260), (750, 380),  # right sleeve
            (630, 380), (620, 800),  # right torso
            (280, 800), (270, 380),  # left torso
            (150, 380), (60, 260), (150, 220),  # left sleeve
            (360, 220),
        ]
        draw.polygon(points, fill=fill, outline=outline)
