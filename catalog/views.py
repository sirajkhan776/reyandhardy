from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .models import Product, Category, WishlistItem
try:
    from core.models import Banner
except Exception:
    Banner = None
from django.db.models import Q, F, DecimalField, ExpressionWrapper, Avg, Count
from reviews.models import ReviewMedia
import json
from PIL import Image
import io



def home(request):
    products = (
        Product.objects.filter(is_active=True)
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
        .order_by("-created_at")[:12]
    )
    categories = Category.objects.all()
    banners = []
    wishlist_ids = []
    if request.user.is_authenticated:
        try:
            wishlist_ids = list(WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True))
        except Exception:
            wishlist_ids = []
    if Banner:
        try:
            banners = list(Banner.objects.filter(is_active=True).order_by("sort_order", "-created_at")[:8])
        except Exception:
            banners = []
    # Category rail from DB only
    category_cards = []
    for c in Category.objects.filter(is_display=True).order_by("name"):
        thumb = ""
        try:
            if c.thumbnail and getattr(c.thumbnail, "url", None):
                thumb = c.thumbnail.url
        except Exception:
            thumb = ""
        if not thumb and c.thumbnail_url:
            thumb = c.thumbnail_url
        category_cards.append({
            "label": c.name,
            "link": f"/category/{c.slug}/",
            "exists": True,
            "thumb": thumb,
        })
    # Top Deals: products with sale price up to ~30% off
    discount_expr = ExpressionWrapper((F("base_price") - F("sale_price")) * 100.0 / F("base_price"), output_field=DecimalField(max_digits=5, decimal_places=2))
    top_deals = (
        Product.objects.filter(is_active=True, sale_price__isnull=False)
        .annotate(discount=discount_expr)
        .filter(discount__gt=0, discount__lte=30)
        .order_by("-discount")[:8]
    )
    return render(
        request,
        "catalog/home.html",
        {
            "products": products,
            "categories": categories,
            "banners": banners,
            "wishlist_ids": wishlist_ids,
            "top_deals": top_deals,
            "category_cards": category_cards,
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True)
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True))
    # Banners for hero
    banners = []
    if Banner:
        try:
            banners = list(Banner.objects.filter(is_active=True).order_by("sort_order", "-created_at")[:3])
        except Exception:
            banners = []
    return render(
        request,
        "catalog/category_detail.html",
        {
            "category": category,
            "products": products,
            "wishlist_ids": wishlist_ids,
            "banners": banners,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    wishlist = []
    if request.user.is_authenticated:
        wishlist = WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)

    # Build distinct, well-ordered size and color lists for the selector
    sizes = []
    colors = []
    if product.variants.exists():
        size_order = ["M", "L", "XL", "XXL"]
        color_order = ["Red", "Black", "Navy Blue", "White", "Grey"]
        raw_sizes = product.variants.values_list("size", flat=True).distinct()
        raw_colors = product.variants.values_list("color", flat=True).distinct()
        sizes = sorted(set(raw_sizes), key=lambda s: (size_order.index(s) if s in size_order else 999, s))
        colors = sorted(set(raw_colors), key=lambda c: (color_order.index(c) if c in color_order else 999, c))

    videos = product.videos.all()
    images = product.images.all()
    # Build color -> first image thumb mapping and color options list
    color_first_img = {}
    try:
        for img in images:
            c = getattr(img, "color", "") or ""
            if c and c not in color_first_img:
                color_first_img[c] = img.image.url if getattr(img.image, "url", None) else ""
    except Exception:
        color_first_img = {}
    color_options = [
        {"name": c, "thumb": color_first_img.get(c, "")}
        for c in colors
    ]
    # Build color -> allowed sizes map for UI filtering
    c2s = {}
    try:
        for v in product.variants.all():
            if not v.color or not v.size:
                continue
            c2s.setdefault(v.color, set()).add(v.size)
    except Exception:
        c2s = {}
    # Order sizes within each color based on sizes order
    def _order_sizes(szs):
        order = {s: i for i, s in enumerate(sizes)}
        return [s for s in sizes if s in szs]
    color_size_map = {c: _order_sizes(szs) for c, szs in c2s.items()}

    # Build nested stock map: color -> size -> stock
    stock_map = {}
    try:
        for v in product.variants.all():
            c = (v.color or "").strip()
            s = (v.size or "").strip()
            if not c or not s:
                continue
            stock_map.setdefault(c, {})[s] = int(getattr(v, "stock", 0) or 0)
    except Exception:
        stock_map = {}
    # Ratings & Reviews summary
    try:
        stats = product.reviews.aggregate(avg_rating=Avg("rating"), rating_count=Count("id"))
        avg_rating = float(stats.get("avg_rating") or 0.0)
        # one decimal place for display
        avg_rating_disp = round(avg_rating + 1e-8, 1)
        rating_count = int(stats.get("rating_count") or 0)
        review_count = rating_count
    except Exception:
        avg_rating_disp = 0.0
        rating_count = 0
        review_count = 0

    # Recent review media (images/videos)
    recent_media = list(ReviewMedia.objects.filter(review__product=product).order_by("-created_at")[0:4])
    total_media_count = ReviewMedia.objects.filter(review__product=product).count()
    remaining_media = max(0, total_media_count - len(recent_media))

    # Latest review
    latest_review = product.reviews.select_related("user").prefetch_related("media").order_by("-created_at").first()

    # Similar products from same category
    similar_qs = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(id=product.id)
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
        .filter(review_count__gt=0)
        .prefetch_related("images")
        .order_by("-avg_rating", "-review_count", "-created_at")
    )
    similar_products = list(similar_qs[:8])
    if not similar_products:
        fallback_qs = (
            Product.objects.filter(is_active=True)
            .exclude(id=product.id)
            .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
            .filter(review_count__gt=0)
            .prefetch_related("images")
            .order_by("-avg_rating", "-review_count", "-created_at")
        )
        similar_products = list(fallback_qs[:8])

    # Preselect from query params for deep-links
    qs_size = (request.GET.get("size") or "").strip()
    qs_color = (request.GET.get("color") or "").strip()

    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "wishlist": wishlist,
            "sizes": sizes,
            "colors": colors,
            "color_options": color_options,
            "videos": videos,
            "images": images,
            "color_size_map_json": json.dumps(color_size_map),
            "sizes_json": json.dumps(list(sizes)),
            "variant_stock_map_json": json.dumps(stock_map),
            # review summary
            "avg_rating": avg_rating_disp,
            "rating_count": rating_count,
            "review_count": review_count,
            "recent_media": recent_media,
            "remaining_media": remaining_media,
            "latest_review": latest_review,
            "similar_products": similar_products,
            "qs_size": qs_size,
            "qs_color": qs_color,
        },
    )


def search(request):
    products = Product.objects.filter(is_active=True)
    title = "Search"
    hint = None
    q = request.GET.get("q", "").strip()
    if request.method == "POST" and request.FILES.get("image"):
        try:
            uploaded = request.FILES["image"].read()
            img = Image.open(io.BytesIO(uploaded)).convert("RGB").resize((64, 64))
            pixels = list(img.getdata())
            # Compute average color
            r = sum(p[0] for p in pixels) / len(pixels)
            g = sum(p[1] for p in pixels) / len(pixels)
            b = sum(p[2] for p in pixels) / len(pixels)
            color = _nearest_color((r, g, b))
            products = products.filter(variants__color=color).distinct()
            title = f"Results by image color: {color}"
            hint = f"Filtered using detected color: {color}"
        except Exception:
            messages.error(request, "Couldn't analyze the image. Showing all products.")
    else:
        if q:
            products = products.filter(Q(name__icontains=q) | Q(description__icontains=q)).distinct()
            title = f"Results for '{q}'"
        else:
            products = products.none()
            title = "Type to search products"
    # Banners for hero
    banners = []
    if Banner:
        try:
            banners = list(Banner.objects.filter(is_active=True).order_by("sort_order", "-created_at")[:3])
        except Exception:
            banners = []
    return render(
        request,
        "catalog/search_results.html",
        {
            "products": products,
            "title": title,
            "hint": hint,
            "banners": banners,
            "q": q,
        },
    )


def _nearest_color(rgb):
    palette = {
        "Red": (239, 68, 68),
        "Black": (17, 24, 39),
        "Navy Blue": (30, 58, 138),
        "White": (250, 250, 250),
        "Grey": (107, 114, 128),
    }
    def dist2(a, b):
        return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2
    best = min(palette.items(), key=lambda kv: dist2(rgb, kv[1]))
    return best[0]


@login_required
def wishlist(request):
    items = (
        WishlistItem.objects.filter(user=request.user)
        .select_related("product")
        .prefetch_related("product__images")
    )
    return render(request, "catalog/wishlist.html", {"items": items})


@login_required
def wishlist_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "Added to wishlist")
    return redirect("product_detail", slug=product.slug)


@login_required
def wishlist_remove(request, product_id):
    WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    messages.info(request, "Removed from wishlist")
    return redirect("wishlist")
