import razorpay
from django.conf import settings


def get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay keys not configured in environment")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_paise: int, receipt: str):
    client = get_razorpay_client()
    data = {"amount": amount_paise, "currency": "INR", "receipt": receipt}
    return client.order.create(data=data)


def verify_razorpay_signature(params: dict) -> bool:
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature(params)
        return True
    except Exception:
        return False

