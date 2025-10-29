import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .utils import verify_razorpay_signature
from orders.models import Order


@csrf_exempt
def razorpay_callback(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    params = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id)

    if verify_razorpay_signature(params):
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = razorpay_signature
        order.status = "paid"
        order.save()
        messages.success(request, f"Payment successful for order {order.order_number}")
        # Clear cart for user if any
        if hasattr(order.user, "cart"):
            order.user.cart.items.all().delete()
        return redirect("order_detail", order_number=order.order_number)

    messages.error(request, "Payment verification failed")
    return redirect("checkout")


@csrf_exempt
def razorpay_webhook(request):
    try:
        data = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    # In a production setup, verify webhook signature header 'X-Razorpay-Signature'
    event = data.get("event")
    payload = data.get("payload", {})
    if event == "payment.captured":
        order_id = payload.get("payment", {}).get("entity", {}).get("order_id")
        if order_id:
            try:
                order = Order.objects.get(razorpay_order_id=order_id)
                order.status = "paid"
                order.save()
            except Order.DoesNotExist:
                pass

    return HttpResponse(status=200)

