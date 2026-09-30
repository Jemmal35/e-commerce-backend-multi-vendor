from decimal import Decimal
import stripe

from django.conf import settings
from .models import Payment, PaymentStatus
from apps.orders.models import Order, OrderStatus

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    @staticmethod
    def initialize_checkout_payment(orders: list[Order], user_email: str) -> dict:
        """
        Initializes a Stripe Checkout Session for the given orders.
        """
        grand_total = sum(order.total_amount for order in orders)
        amount_in_cents = int((grand_total * Decimal('100')).quantize(Decimal('1')))
        order_ids_str = ','.join(str(order.id) for order in orders)
        
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=settings.STRIPE_CURRENCY.lower(),
            receipt_email=user_email,
            metadata={'order_ids': order_ids_str},
            automatic_payment_methods={'enabled': True},
        )
        
        payment_record = []
        for order in orders:
            payment = Payment.objects.create(
                order=order,
                stripe_payment_intent_id=intent.id,
                amount=order.total_amount,
                currency=settings.STRIPE_CURRENCY,
                status=PaymentStatus.REQUIRES_ACTION,
                metadata={'stripe_client_secret': intent.client_secret}
            )
            payment_record.append(payment)
        
        return {
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            'grand_total': grand_total,
        }
