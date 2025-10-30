from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import UserProfile
from orders.models import Order
from catalog.models import ProductImage
from .models import Address
from django.contrib.sessions.models import Session
from django.utils import timezone


@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        # Update username, interests, avatar
        new_username = request.POST.get("username", "").strip()
        interests = request.POST.get("interests", "").strip()
        avatar = request.FILES.get("avatar")
        if new_username and new_username != request.user.username:
            try:
                request.user.username = new_username
                request.user.save()
                messages.success(request, "Username updated")
            except Exception:
                messages.error(request, "Could not update username (maybe taken)")
        if interests is not None:
            profile.interests = interests
        if avatar:
            profile.avatar = avatar
        profile.save()
        messages.success(request, "Profile updated")
        return redirect("profile")
    if request.method == "POST":
        profile.phone = request.POST.get("phone", "")
        profile.address_line1 = request.POST.get("address_line1", "")
        profile.address_line2 = request.POST.get("address_line2", "")
        profile.city = request.POST.get("city", "")
        profile.state = request.POST.get("state", "")
        profile.postal_code = request.POST.get("postal_code", "")
        profile.country = request.POST.get("country", "India")
        profile.save()
        messages.success(request, "Profile updated")
        return redirect("profile")

    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def you(request):
    # Handle profile update from modal
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        new_username = request.POST.get("username", "").strip()
        interests = request.POST.get("interests", "").strip()
        avatar = request.FILES.get("avatar")
        # Update username if provided and different
        if new_username and new_username != request.user.username:
            try:
                request.user.username = new_username
                request.user.save()
                messages.success(request, "Username updated")
            except Exception:
                messages.error(request, "Could not update username (maybe taken)")
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if interests is not None:
            profile.interests = interests
        if avatar:
            profile.avatar = avatar
        profile.save()
        return redirect("you")
    orders = Order.objects.filter(user=request.user).order_by("-created_at")[:8]
    order_cards = []
    for o in orders:
        # take first item image if available
        img_url = None
        first_item = o.items.first()
        if first_item:
            try:
                p = first_item.product
                img = p.images.first()
                if img and img.image:
                    img_url = img.image.url
            except Exception:
                img_url = None
        order_cards.append({
            "order": o,
            "img": img_url,
            "link": f"/order/{o.order_number}/",
        })

    # Buy Again: recent distinct products from latest orders
    recent_items = []
    seen = set()
    for o in Order.objects.filter(user=request.user).order_by("-created_at")[:10]:
        for it in o.items.all():
            pid = it.product_id
            if pid in seen:
                continue
            seen.add(pid)
            img = it.product.images.first()
            recent_items.append({
                "product": it.product,
                "img": img.image.url if img else None,
                "link": f"/product/{it.product.slug}/",
            })
            if len(recent_items) >= 8:
                break
        if len(recent_items) >= 8:
            break

    return render(request, "accounts/you.html", {
        "order_cards": order_cards,
        "buy_again": recent_items,
        "profile": getattr(request.user, "profile", None),
    })


def help_center(request):
    delivered = []
    if request.user.is_authenticated:
        qs = Order.objects.filter(user=request.user, status="delivered").order_by("-updated_at")[:3]
        for o in qs:
            img_url = None
            first_item = o.items.first()
            if first_item:
                try:
                    img = first_item.product.images.first()
                    if img and img.image:
                        img_url = img.image.url
                except Exception:
                    img_url = None
            delivered.append({
                "order": o,
                "img": img_url,
                "link": f"/order/{o.order_number}/help/",
            })
    return render(request, "accounts/help_center.html", {"delivered": delivered})


@login_required
def addresses(request):
    next_url = request.GET.get("next", "")
    editing = request.GET.get("edit")
    editing_addr = None
    if editing:
        try:
            editing_addr = Address.objects.get(user=request.user, id=int(editing))
        except (Address.DoesNotExist, ValueError, TypeError):
            editing_addr = None

    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "create":
            addr = Address.objects.create(
                user=request.user,
                full_name=request.POST.get("full_name", request.user.get_full_name() or request.user.username),
                phone=request.POST.get("phone", ""),
                address_line1=request.POST.get("address_line1", ""),
                address_line2=request.POST.get("address_line2", ""),
                city=request.POST.get("city", ""),
                state=request.POST.get("state", ""),
                postal_code=request.POST.get("postal_code", ""),
                country=request.POST.get("country", "India"),
            )
            if request.POST.get("is_default"):
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                addr.is_default = True
                addr.save()
            messages.success(request, "Address added")
            return redirect("addresses")
        elif action == "update":
            try:
                addr = Address.objects.get(user=request.user, id=int(request.POST.get("id")))
                addr.full_name = request.POST.get("full_name", addr.full_name)
                addr.phone = request.POST.get("phone", addr.phone)
                addr.address_line1 = request.POST.get("address_line1", addr.address_line1)
                addr.address_line2 = request.POST.get("address_line2", addr.address_line2)
                addr.city = request.POST.get("city", addr.city)
                addr.state = request.POST.get("state", addr.state)
                addr.postal_code = request.POST.get("postal_code", addr.postal_code)
                addr.country = request.POST.get("country", addr.country)
                if request.POST.get("is_default"):
                    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                    addr.is_default = True
                addr.save()
                messages.success(request, "Address updated")
            except Exception:
                messages.error(request, "Could not update address")
            return redirect("addresses")

    addrs = Address.objects.filter(user=request.user)
    return render(request, "accounts/addresses.html", {"addresses": addrs, "next": next_url, "editing": editing_addr})


@login_required
def address_delete(request, pk: int):
    Address.objects.filter(user=request.user, pk=pk).delete()
    messages.info(request, "Address removed")
    return redirect("addresses")


@login_required
def address_make_default(request, pk: int):
    addr = get_object_or_404(Address, user=request.user, pk=pk)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    addr.is_default = True
    addr.save()
    messages.success(request, "Default address set")
    return redirect("addresses")


@login_required
def signout_all_sessions(request):
    if request.method != "POST":
        return redirect("profile")
    uid = str(request.user.pk)
    # Delete all active sessions for this user (including current)
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if str(data.get("_auth_user_id")) == uid:
            session.delete()
    # Ensure current request is logged out too
    logout(request)
    messages.info(request, "Signed out from all sessions.")
    return redirect("account_login")


@login_required
def delete_account(request):
    if request.method != "POST":
        return redirect("profile")
    user = request.user
    # Remove sessions for the user
    uid = str(user.pk)
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if str(data.get("_auth_user_id")) == uid:
            session.delete()

    # Soft-delete: deactivate and anonymize to preserve orders integrity
    # Clear profile PII if present
    try:
        prof = user.profile
        prof.avatar = None
        prof.phone = ""
        prof.address_line1 = ""
        prof.address_line2 = ""
        prof.city = ""
        prof.state = ""
        prof.postal_code = ""
        prof.country = prof.country or ""
        prof.interests = ""
        prof.save()
    except UserProfile.DoesNotExist:
        pass

    # Remove saved addresses
    Address.objects.filter(user=user).delete()

    # Deactivate and make credentials unusable
    user.is_active = False
    try:
        user.username = f"deleted_{user.pk}"
    except Exception:
        pass
    user.email = ""
    user.set_unusable_password()
    user.first_name = ""
    user.last_name = ""
    user.save()

    logout(request)
    messages.success(request, "Your account has been deleted.")
    return redirect("/")
