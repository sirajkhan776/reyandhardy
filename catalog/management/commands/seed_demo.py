import io
import random
from decimal import Decimal
from typing import List

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile, File

from catalog.models import Category, Product, Variant, ProductImage
from coupons.models import Coupon
from reviews.models import Review
from core.models import Banner


class Command(BaseCommand):
    help = "Seed demo data: categories, products (with variants, images), coupons, users, reviews"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Seed even if database is not empty (use with caution)",
        )

    sizes = ["M", "L", "XL", "XXL"]
    colors = ["Black", "Beige", "Navy Blue", "Grey", "White", "Red"]

    def handle(self, *args, **options):
        force = options.get("force", False)

        # Only seed when DB is empty unless --force is provided
        if not force and not self._is_db_empty():
            self.stdout.write(
                self.style.WARNING(
                    "Database is not empty. Skipping seeding. Run with --force to seed anyway."
                )
            )
            return

        self.stdout.write("Seeding demo data…")
        self.seed_categories()
        products = self.seed_products_real()
        self.seed_coupons()
        users = self.seed_users()
        self.seed_reviews(users, products)
        self.seed_banners_videos()
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _is_db_empty(self) -> bool:
        """Consider DB empty if no categories or products (and related items) exist."""
        has_categories = Category.objects.exists()
        has_products = Product.objects.exists()
        has_variants = Variant.objects.exists()
        try:
            from core.models import Banner  # local import to avoid circulars

            has_banners = Banner.objects.exists()
        except Exception:
            has_banners = False
        return not (has_categories or has_products or has_variants or has_banners)

    def seed_categories(self):
        """Create common categories with thumbnails from media/categories and set is_display=True."""
        cat_files = {
            "T-shirts": "media/categories/tshirtthumb.jpg",
            "Shirts": "media/categories/shirtthumb.jpg",
            "Jeans": "media/categories/jeansthumb.jpg",
            "Jackets": "media/categories/jacketthumb.jpg",
            "Formal Wear": "media/categories/formalwear_thumb.jpg",
            "Sweatshirts": "media/categories/sweatshirtthumb.jpg",
            "Wedding": "media/categories/weddingthumb.jpeg",
        }
        for name, path in cat_files.items():
            cat, _ = Category.objects.get_or_create(name=name, defaults={"is_display": True})
            # Attach thumbnail if present
            try:
                with open(path, "rb") as fh:
                    cat.thumbnail.save(path.split("/")[-1], File(fh), save=False)
                cat.is_display = True
                cat.save()
            except FileNotFoundError:
                cat.is_display = True
                cat.save()

    def seed_products_real(self) -> List[Product]:
        """Create real products with variants and color-tagged images from media/products."""
        products: List[Product] = []
        jeans = Category.objects.get_or_create(name="Jeans", defaults={"is_display": True})[0]

        # 1) Men's Slim Fit Cotton Stretch Pants (Black variants + black images)
        pants_desc = (
            "These slim-fit cotton stretch pants offer a perfect blend of comfort and style. "
            "Made from premium breathable fabric, they’re ideal for casual outings, office wear, or semi-formal events. "
            "Pair them with shirts or t-shirts for a smart look.\n\n"
            "\U0001F4CB Key Features\n\n"
            "Material: 98% Cotton, 2% Spandex\n\n"
            "Fit Type: Slim Fit\n\n"
            "Closure: Button and Zip Fly\n\n"
            "Pockets: 2 front, 2 back\n\n"
            "Stretchable and comfortable fabric\n\n"
            "Easy to wash and maintain."
        )
        p1 = self._create_product(
            name="Men’s Slim Fit Cotton Stretch Pants",
            category=jeans,
            base_price=Decimal("1000.00"),
            sale_price=Decimal("499.00"),
            description=pants_desc,
        )
        # Images for Black
        self._attach_image_from_file(p1, "media/products/blackcolorpant.jpg", color="Black", primary=True)
        self._attach_image_from_file(p1, "media/products/black-2.jpg", color="Black", primary=False)
        # Variants: Black M/L/XL/XXL stock 10
        for sz in ["M", "L", "XL", "XXL"]:
            self._ensure_variant(p1, sz, "Black", stock=10)

        # 2) Beige pants from provided image
        p2 = self._create_product(
            name="Men’s Slim Fit Stretch Pants (Beige)",
            category=jeans,
            base_price=Decimal("999.00"),
            sale_price=Decimal("499.00"),
            description="Slim fit stretch pants in beige for all-day comfort.",
        )
        self._attach_image_from_file(p2, "media/products/beigecolorpant.avif", color="Beige", primary=True)
        for sz in ["M", "L", "XL"]:
            self._ensure_variant(p2, sz, "Beige", stock=10)

        # 3) Navy blue pants
        p3 = self._create_product(
            name="Men’s Slim Fit Stretch Pants (Navy Blue)",
            category=jeans,
            base_price=Decimal("999.00"),
            sale_price=Decimal("549.00"),
            description="Navy blue slim pants with clean lines and stretch.",
        )
        self._attach_image_from_file(p3, "media/products/navybluepant.webp", color="Navy Blue", primary=True)
        for sz in ["M", "L", "XL"]:
            self._ensure_variant(p3, sz, "Navy Blue", stock=10)

        # 4) Classic Black formal pants
        p4 = self._create_product(
            name="Classic Black Formal Pants",
            category=jeans,
            base_price=Decimal("899.00"),
            sale_price=Decimal("499.00"),
            description="Classic black pants suitable for work and evenings.",
        )
        self._attach_image_from_file(p4, "media/products/Pant.jpg", color="Black", primary=True)
        for sz in ["M", "L"]:
            self._ensure_variant(p4, sz, "Black", stock=8)

        # 5) Everyday Stretch Pants (Grey)
        p5 = self._create_product(
            name="Everyday Stretch Pants (Grey)",
            category=jeans,
            base_price=Decimal("899.00"),
            sale_price=Decimal("499.00"),
            description="Everyday stretch comfort in a versatile grey.",
        )
        self._attach_image_from_file(p5, "media/products/pant2.jpg", color="Grey", primary=True)
        for sz in ["M", "XL"]:
            self._ensure_variant(p5, sz, "Grey", stock=6)

        # 6) Lightweight Pants (Black)
        p6 = self._create_product(
            name="Lightweight Cotton Pants",
            category=jeans,
            base_price=Decimal("799.00"),
            sale_price=Decimal("499.00"),
            description="Lightweight cotton pants for daily wear.",
        )
        self._attach_image_from_file(p6, "media/products/pant1.avif", color="Black", primary=True)
        for sz in ["L", "XXL"]:
            self._ensure_variant(p6, sz, "Black", stock=5)

        return [p1, p2, p3, p4, p5, p6]

    # Helpers for real products
    def _create_product(self, name: str, category: Category, base_price: Decimal, sale_price: Decimal | None, description: str) -> Product:
        slug = slugify(name)
        p, _ = Product.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "category": category,
                "description": description,
                "base_price": base_price,
                "sale_price": sale_price,
                "is_active": True,
            },
        )
        return p

    def _attach_image_from_file(self, product: Product, path: str, color: str = "", primary: bool = False):
        try:
            with open(path, "rb") as fh:
                img_file = File(fh)
                # If primary, clear previous primaries
                if primary:
                    product.images.update(is_primary=False)
                ProductImage.objects.create(
                    product=product,
                    image=img_file,
                    alt_text=f"{product.name}",
                    is_primary=primary,
                    color=color,
                )
        except FileNotFoundError:
            pass

    def _ensure_variant(self, product: Product, size: str, color: str, stock: int = 10):
        Variant.objects.get_or_create(
            product=product,
            size=size,
            color=color,
            defaults={
                "sku": self._sku_for(product, size, color),
                "stock": stock,
            },
        )

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

    def seed_banners_videos(self):
        """Add two active video banners using provided files."""
        video_paths = [
            "media/banners/videos/853800-hd_1920_1080_25fps.mp4",
            "media/banners/videos/5822804-hd_1920_1080_25fps_1.mp4",
        ]
        order = 0
        for vp in video_paths:
            order += 1
            try:
                with open(vp, "rb") as fh:
                    video_file = File(fh)
                    Banner.objects.create(
                        title="New collection",
                        subtitle="Premium fits for every day",
                        video=video_file,
                        link_url="/",
                        button_text="Shop now",
                        sort_order=order,
                        is_active=True,
                    )
            except FileNotFoundError:
                continue

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
