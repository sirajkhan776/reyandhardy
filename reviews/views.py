from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import Review, ReviewMedia
from catalog.models import Product


@login_required
def add_review(request, product_id):
    if request.method != "POST":
        return redirect("product_detail", slug=get_object_or_404(Product, id=product_id).slug)

    product = get_object_or_404(Product, id=product_id)
    rating = int(request.POST.get("rating", 0))
    title = request.POST.get("title", "")
    body = request.POST.get("body", "")
    if rating < 1 or rating > 5:
        messages.error(request, "Invalid rating")
        return redirect("product_detail", slug=product.slug)

    review, _created = Review.objects.update_or_create(
        user=request.user, product=product, defaults={"rating": rating, "title": title, "body": body}
    )

    # Handle uploaded media (images/videos)
    files = []
    files.extend(request.FILES.getlist("media"))
    files.extend(request.FILES.getlist("photos"))
    if request.FILES.get("video"):
        files.append(request.FILES["video"])

    saved_photos = 0
    saved_video = False
    for f in files:
        ctype = getattr(f, 'content_type', '') or ''
        if ctype.startswith('image/'):
            if saved_photos >= 4:
                continue
            if hasattr(f, 'size') and f.size and f.size > 20 * 1024 * 1024:
                continue
            ReviewMedia.objects.create(review=review, file=f, kind='image')
            saved_photos += 1
        elif ctype.startswith('video/'):
            if saved_video:
                continue
            if hasattr(f, 'size') and f.size and f.size > 200 * 1024 * 1024:
                continue
            ReviewMedia.objects.create(review=review, file=f, kind='video')
            saved_video = True
    messages.success(request, "Review submitted")
    next_url = request.POST.get("next", "")
    if next_url and isinstance(next_url, str) and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("product_detail", slug=product.slug)


@login_required
def write_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        rating = int(request.GET.get("rating", 0))
    except Exception:
        rating = 0
    rating = rating if 1 <= rating <= 5 else 0
    next_url = request.GET.get("next", "")

    labels = {1: ("Sad", "😞"), 2: ("Bad", "😕"), 3: ("Moody", "😐"), 4: ("Liked it", "🙂"), 5: ("Superb", "🤩")}
    label_text, label_emoji = labels.get(rating, ("", ""))
    thumb = None
    try:
        img = product.images.all().first()
        if img and getattr(img.image, 'url', None):
            thumb = img.image.url
    except Exception:
        thumb = None

    return render(
        request,
        "reviews/write_review.html",
        {
            "product": product,
            "rating": rating,
            "rating_label": label_text,
            "rating_emoji": label_emoji,
            "thumb": thumb,
            "next": next_url,
        },
    )


def product_media(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    media = ReviewMedia.objects.filter(review__product=product).order_by('-created_at')
    return render(
        request,
        'reviews/product_media.html',
        {
            'product': product,
            'media': media,
            'count': media.count(),
        }
    )


def product_reviews(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    reviews = (
        Review.objects.filter(product=product)
        .select_related('user')
        .prefetch_related('media')
        .order_by('-created_at')
    )
    return render(
        request,
        'reviews/product_reviews.html',
        {
            'product': product,
            'reviews': reviews,
            'count': reviews.count(),
        }
    )
