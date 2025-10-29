from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Review
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

    Review.objects.update_or_create(
        user=request.user, product=product, defaults={"rating": rating, "title": title, "body": body}
    )
    messages.success(request, "Review submitted")
    return redirect("product_detail", slug=product.slug)

