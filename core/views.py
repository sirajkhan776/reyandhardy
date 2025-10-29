from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import NewsletterSubscriber


@require_POST
def newsletter_subscribe(request):
    email = (request.POST.get("email") or "").strip().lower()
    if not email:
        messages.error(request, "Please enter a valid email")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    try:
        obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if created:
            messages.success(request, "Thanks for subscribing!")
        else:
            messages.info(request, "You're already subscribed.")
    except Exception:
        messages.error(request, "Unable to subscribe right now. Please try later.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

