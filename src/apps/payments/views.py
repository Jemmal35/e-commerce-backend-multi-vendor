import json
import traceback
from apps.orders.tasks import process_failed_payment_task, process_successful_payment_task
import stripe

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.orders.models import Order, OrderStatus
from .models import Payment, PaymentStatus

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        payload = request.body
        sig_header = request.headers.get('Stripe-Signature')
        event = None

        print("=== STRIPE WEBHOOK DEBUG START ===")
        print(f"Payload length: {len(payload)}")
        print(f"Signature header: {sig_header}")
        print(f"Configured Webhook Secret (first 10 chars): {settings.STRIPE_WEBHOOK_SECRET[:10]}...")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            print("Webhook signature verification SUCCESS!")
        except ValueError as e:
            print(f"CRITICAL WEBHOOK ERROR (ValueError): {e}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            print(f"CRITICAL WEBHOOK ERROR (SignatureVerificationError): {e}")
            return HttpResponse(status=400)
        except Exception as e:
            print(f"CRITICAL WEBHOOK ERROR (Unexpected {type(e).__name__}): {e}")
            traceback.print_exc()
            return HttpResponse(status=400)

        # Handle event types
        event_type = event.get('type') if isinstance(event, dict) else event.type
        
        if event_type == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_payment_success(payment_intent)
        
        elif event_type == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self._handle_payment_failure(payment_intent)

        return HttpResponse(status=200)
    
    def _handle_payment_success(self, intent):
        payment_intent_id = intent.get("id") if hasattr(intent, "get") else intent.id
        
        with transaction.atomic():
            payments = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).select_for_update()
            
            for payment in payments:
                if payment.status == PaymentStatus.SUCCEEDED:
                    continue
                
                payment.status = PaymentStatus.SUCCEEDED
                payment.metadata['stripe_event_id'] = payment_intent_id
                payment.save(update_fields=["status", "metadata", "updated_at"])
                
                order = payment.order
                order.status = OrderStatus.PAID
                order.payment_status = PaymentStatus.SUCCEEDED
                order.save(update_fields=["status", "payment_status", "updated_at"])
                
                transaction.on_commit(
                    lambda o_id=order.id: process_successful_payment_task.delay(o_id)
                )
                
    def _handle_payment_failure(self, intent):
        payment_intent_id = intent.get("id") if hasattr(intent, "get") else intent.id
        
        # Safely extract failure error message from StripeObject
        last_error = getattr(intent, "last_payment_error", None)
        failure_reason = "Payment failed"
        if last_error:
            failure_reason = getattr(last_error, "message", "Payment failed")
        
        with transaction.atomic():
            payments = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).select_for_update()
            
            for payment in payments:
                payment.status = PaymentStatus.FAILED
                payment.metadata["failure_reason"] = failure_reason
                payment.save(update_fields=["status", "metadata", "updated_at"])
                
                order = payment.order
                order.status = OrderStatus.CANCELLED
                order.payment_status = PaymentStatus.FAILED
                order.save(update_fields=["status", "payment_status", "updated_at"])
                
                transaction.on_commit(
                    lambda o_id=order.id: process_failed_payment_task.delay(o_id)
                )