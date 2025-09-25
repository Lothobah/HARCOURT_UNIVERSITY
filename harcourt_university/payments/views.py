
# payments/views.py
import stripe
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from .models import (Payment, TutorSubscription, Refund, Wallet, WalletTransaction, 
                     SessionPackage, PurchasedPackage)
from .forms import RefundRequestForm
from tutoring.models import TutoringSession
from resources.models import Resource, VideoLesson
from accounts.models import TutorProfile

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Payment statistics
        payments = self.get_queryset()
        context['stats'] = {
            'total_spent': payments.filter(status='completed').aggregate(
                total=models.Sum('amount')
            )['total'] or 0,
            'pending_payments': payments.filter(status='pending').count(),
            'completed_payments': payments.filter(status='completed').count(),
        }
        
        return context


class PayForSessionView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(TutoringSession, id=session_id)
        
        # Verify user can pay for this session
        if session.student != request.user:
            messages.error(request, 'You cannot pay for this session.')
            return redirect('tutoring:session_detail', pk=session_id)
        
        # Check if already paid
        if Payment.objects.filter(session=session, status='completed').exists():
            messages.info(request, 'This session has already been paid for.')
            return redirect('tutoring:session_detail', pk=session_id)
        
        context = {
            'session': session,
            'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        
        return render(request, 'payments/pay_session.html', context)
    
    def post(self, request, session_id):
        session = get_object_or_404(TutoringSession, id=session_id)
        payment_method = request.POST.get('payment_method', 'stripe')
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            payment_type='session',
            amount=session.total_amount,
            payment_method=payment_method,
            session=session,
            description=f'Payment for session: {session.title}',
        )
        
        if payment_method == 'stripe':
            return self.process_stripe_payment(request, payment)
        elif payment_method == 'wallet':
            return self.process_wallet_payment(request, payment)
        elif payment_method in ['mtn_momo', 'vodafone_cash']:
            return self.process_mobile_money_payment(request, payment)
        
        messages.error(request, 'Invalid payment method.')
        return redirect('payments:pay_session', session_id=session_id)
    
    def process_stripe_payment(self, request, payment):
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Stripe expects amount in cents
                currency='ghs',
                metadata={
                    'payment_id': str(payment.id),
                    'user_id': str(request.user.id),
                }
            )
            
            payment.stripe_payment_intent_id = intent.id
            payment.save()
            
            return JsonResponse({
                'client_secret': intent.client_secret,
                'payment_id': str(payment.id),
            })
            
        except stripe.error.StripeError as e:
            payment.status = 'failed'
            payment.save()
            return JsonResponse({'error': str(e)}, status=400)
    
    def process_wallet_payment(self, request, payment):
        try:
            wallet = request.user.wallet
            if wallet.has_sufficient_balance(payment.amount):
                if wallet.deduct_funds(payment.amount, f'Payment for session: {payment.session.title}'):
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.save()
                    
                    # Update session status
                    payment.session.status = 'confirmed'
                    payment.session.save()
                    
                    messages.success(request, 'Payment successful!')
                    return redirect('tutoring:session_detail', pk=payment.session.id)
            
            messages.error(request, 'Insufficient wallet balance.')
            payment.status = 'failed'
            payment.save()
            
        except Exception as e:
            messages.error(request, 'Payment failed. Please try again.')
            payment.status = 'failed'
            payment.save()
        
        return redirect('payments:pay_session', session_id=payment.session.id)
    
    def process_mobile_money_payment(self, request, payment):
        # Implement mobile money payment logic here
        # This would integrate with local payment providers like MTN MoMo, Vodafone Cash
        phone_number = request.POST.get('phone_number')
        
        # For now, we'll mark as pending and require manual verification
        payment.status = 'pending'
        payment.metadata = {'phone_number': phone_number}
        payment.save()
        
        messages.info(request, 'Mobile money payment initiated. You will receive a prompt shortly.')
        return redirect('payments:payment_list')


class SubscriptionView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/subscription.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user is a tutor
        if not self.request.user.is_tutor:
            return context
        
        # Get current subscription
        try:
            context['current_subscription'] = self.request.user.subscription
        except TutorSubscription.DoesNotExist:
            context['current_subscription'] = None
        
        # Subscription plans
        context['plans'] = [
            {
                'name': 'Basic',
                'price': 50,
                'duration': '1 month',
                'features': [
                    'Up to 10 students',
                    'Basic profile visibility',
                    'Email support',
                    'Basic analytics'
                ]
            },
            {
                'name': 'Standard',
                'price': 120,
                'duration': '3 months',
                'features': [
                    'Up to 25 students',
                    'Enhanced profile visibility',
                    'Priority email support',
                    'Advanced analytics',
                    'Resource upload'
                ]
            },
            {
                'name': 'Premium',
                'price': 200,
                'duration': '6 months',
                'features': [
                    'Unlimited students',
                    'Featured profile placement',
                    'Phone support',
                    'Complete analytics suite',
                    'Unlimited resource uploads',
                    'Video lesson creation'
                ]
            }
        ]
        
        return context
    
    def post(self, request):
        if not request.user.is_tutor:
            messages.error(request, 'Only tutors can subscribe to plans.')
            return redirect('accounts:dashboard')
        
        plan = request.POST.get('plan')
        payment_method = request.POST.get('payment_method', 'stripe')
        
        # Plan pricing
        plan_prices = {
            'basic': {'amount': 50, 'months': 1},
            'standard': {'amount': 120, 'months': 3},
            'premium': {'amount': 200, 'months': 6},
        }
        
        if plan not in plan_prices:
            messages.error(request, 'Invalid subscription plan.')
            return redirect('payments:subscription')
        
        # Create payment
        payment = Payment.objects.create(
            user=request.user,
            payment_type='subscription',
            amount=plan_prices[plan]['amount'],
            payment_method=payment_method,
            description=f'Tutor subscription - {plan.title()} plan',
            metadata={'plan': plan, 'months': plan_prices[plan]['months']}
        )
        
        if payment_method == 'stripe':
            # Create Stripe payment intent
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(payment.amount * 100),
                    currency='ghs',
                    metadata={
                        'payment_id': str(payment.id),
                        'plan': plan,
                    }
                )
                
                return JsonResponse({'client_secret': intent.client_secret})
                
            except stripe.error.StripeError as e:
                payment.delete()
                return JsonResponse({'error': str(e)}, status=400)
        
        return redirect('payments:payment_list')


class WalletView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/wallet.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        context['wallet'] = wallet
        
        # Recent transactions
        context['transactions'] = wallet.transactions.order_by('-created_at')[:20]
        
        return context
    
    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'topup':
            amount = Decimal(request.POST.get('amount', '0'))
            if amount > 0:
                # Create payment for wallet top-up
                payment = Payment.objects.create(
                    user=request.user,
                    payment_type='wallet_topup',
                    amount=amount,
                    payment_method=request.POST.get('payment_method', 'stripe'),
                    description=f'Wallet top-up - GHS {amount}',
                )
                
                # Process payment (simplified)
                if payment.payment_method == 'stripe':
                    try:
                        intent = stripe.PaymentIntent.create(
                            amount=int(amount * 100),
                            currency='ghs',
                            metadata={'payment_id': str(payment.id)}
                        )
                        return JsonResponse({'client_secret': intent.client_secret})
                    except stripe.error.StripeError as e:
                        payment.delete()
                        return JsonResponse({'error': str(e)}, status=400)
        
        return redirect('payments:wallet')


class RequestRefundView(LoginRequiredMixin, CreateView):
    model = Refund
    form_class = RefundRequestForm
    template_name = 'payments/request_refund.html'
    success_url = reverse_lazy('payments:payment_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_id = self.kwargs.get('payment_id')
        context['payment'] = get_object_or_404(Payment, id=payment_id, user=self.request.user)
        return context
    
    def form_valid(self, form):
        payment_id = self.kwargs.get('payment_id')
        payment = get_object_or_404(Payment, id=payment_id, user=self.request.user)
        
        # Check if payment is eligible for refund
        if payment.status != 'completed':
            messages.error(self.request, 'Only completed payments can be refunded.')
            return redirect('payments:payment_list')
        
        # Check if refund already exists
        if hasattr(payment, 'refund'):
            messages.error(self.request, 'Refund request already exists for this payment.')
            return redirect('payments:payment_list')
        
        form.instance.payment = payment
        if not form.instance.amount:
            form.instance.amount = payment.amount
        
        response = super().form_valid(form)
        messages.success(self.request, 'Refund request submitted successfully.')
        return response


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET if hasattr(settings, 'STRIPE_WEBHOOK_SECRET') else None
        
        try:
            if endpoint_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            else:
                event = json.loads(payload)
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            self.handle_payment_success(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            self.handle_payment_failure(event['data']['object'])
        
        return HttpResponse(status=200)
    
    def handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        try:
            payment_id = payment_intent['metadata'].get('payment_id')
            payment = Payment.objects.get(id=payment_id)
            
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.gateway_response = payment_intent
            payment.save()
            
            # Handle different payment types
            if payment.payment_type == 'session' and payment.session:
                payment.session.status = 'confirmed'
                payment.session.save()
                
            elif payment.payment_type == 'subscription':
                self.create_tutor_subscription(payment)
                
            elif payment.payment_type == 'wallet_topup':
                wallet, created = Wallet.objects.get_or_create(user=payment.user)
                wallet.add_funds(payment.amount, 'Wallet top-up via Stripe')
            
        except Payment.DoesNotExist:
            pass  # Payment not found, might be from different system
    
    def handle_payment_failure(self, payment_intent):
        """Handle failed payment"""
        try:
            payment_id = payment_intent['metadata'].get('payment_id')
            payment = Payment.objects.get(id=payment_id)
            
            payment.status = 'failed'
            payment.gateway_response = payment_intent
            payment.save()
            
        except Payment.DoesNotExist:
            pass
    
    def create_tutor_subscription(self, payment):
        """Create tutor subscription after successful payment"""
        plan = payment.metadata.get('plan')
        months = payment.metadata.get('months', 1)
        
        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=30 * months)
        
        # Get or create subscription
        subscription, created = TutorSubscription.objects.get_or_create(
            tutor=payment.user,
            defaults={
                'plan': plan,
                'start_date': start_date,
                'end_date': end_date,
                'amount_paid': payment.amount,
                'payment': payment,
            }
        )
        
        if not created:
            # Update existing subscription
            subscription.plan = plan
            subscription.end_date = max(subscription.end_date, timezone.now()) + timezone.timedelta(days=30 * months)
            subscription.amount_paid += payment.amount
            subscription.status = 'active'
            subscription.save()
        
        # Update tutor profile
        tutor_profile = payment.user.tutor_profile
        tutor_profile.subscription_active = True
        tutor_profile.subscription_expiry = subscription.end_date
        tutor_profile.save()


def ajax_check_payment_status(request, payment_id):
    """AJAX endpoint to check payment status"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)
        return JsonResponse({
            'status': payment.status,
            'completed': payment.status == 'completed',
        })
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)