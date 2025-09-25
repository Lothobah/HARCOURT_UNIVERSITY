#payments models 
import uuid
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from tutoring.models import TutoringSession
from resources.models import Resource, VideoLesson

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('session', 'Tutoring Session'),
        ('subscription', 'Tutor Subscription'),
        ('resource', 'Resource Purchase'),
        ('video', 'Video Lesson'),
        ('package', 'Session Package'),
        ('wallet_topup', 'Wallet Top-up'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paystack', 'Paystack'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('vodafone_cash', 'Vodafone Cash'),
        ('airteltigo_money', 'AirtelTigo Money'),
        ('wallet', 'Wallet Balance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Related objects
    session = models.ForeignKey(TutoringSession, on_delete=models.CASCADE, blank=True, null=True)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, blank=True, null=True)
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, blank=True, null=True)
    
    # Payment gateway fields
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    paystack_reference = models.CharField(max_length=200, blank=True)
    momo_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)
    
    description = models.CharField(max_length=255)
    metadata = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment {self.id} - {self.user.get_full_name()} - {self.amount} {self.currency}"

    @property
    def is_successful(self):
        return self.status == 'completed'

    class Meta:
        ordering = ['-created_at']


class TutorSubscription(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic Plan'),
        ('standard', 'Standard Plan'),
        ('premium', 'Premium Plan'),
        ('professional', 'Professional Plan'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]

    tutor = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renewal = models.BooleanField(default=False)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    
    # Plan features
    max_students = models.IntegerField(default=10)
    max_resources = models.IntegerField(default=50)
    can_create_groups = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    analytics_access = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tutor.get_full_name()} - {self.plan} ({self.status})"

    @property
    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()

    @property
    def days_remaining(self):
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0

    class Meta:
        ordering = ['-created_at']


class Refund(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]

    REASON_CHOICES = [
        ('session_cancelled', 'Session Cancelled'),
        ('poor_quality', 'Poor Quality'),
        ('technical_issues', 'Technical Issues'),
        ('duplicate_payment', 'Duplicate Payment'),
        ('unauthorized', 'Unauthorized Transaction'),
        ('other', 'Other'),
    ]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='refund')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reason_detail = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    admin_notes = models.TextField(blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"Refund for Payment {self.payment.id} - {self.amount} {self.payment.currency}"

    class Meta:
        ordering = ['-requested_at']


class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Wallet - {self.balance} GHS"

    def add_funds(self, amount, description="", transaction_type='credit'):
        """Add funds to wallet"""
        if amount > 0:
            self.balance += amount
            self.save()
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                balance_after=self.balance
            )
            return True
        return False

    def deduct_funds(self, amount, description=""):
        """Deduct funds from wallet"""
        if self.balance >= amount and amount > 0:
            self.balance -= amount
            self.save()
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type='debit',
                amount=amount,
                description=description,
                balance_after=self.balance
            )
            return True
        return False

    def has_sufficient_balance(self, amount):
        return self.balance >= amount


class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.title()} - {self.amount} GHS"

    class Meta:
        ordering = ['-created_at']


class SessionPackage(models.Model):
    """Predefined packages for multiple sessions"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    sessions_count = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.sessions_count} sessions"

    @property
    def price_per_session(self):
        return self.price / self.sessions_count if self.sessions_count > 0 else 0


class PurchasedPackage(models.Model):
    """User's purchased session packages"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='purchased_packages')
    package = models.ForeignKey(SessionPackage, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    sessions_remaining = models.IntegerField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.package.name}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def use_session(self):
        """Use one session from the package"""
        if self.sessions_remaining > 0 and not self.is_expired:
            self.sessions_remaining -= 1
            if self.sessions_remaining == 0:
                self.is_active = False
            self.save()
            return True
        return False


class Invoice(models.Model):
    """Invoice for payments"""
    invoice_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='invoices')
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    
    # Invoice details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    
    # Status
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d")
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f"INV{timestamp}"
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_number = int(last_invoice.invoice_number[-3:])
                new_number = f"INV{timestamp}{str(last_number + 1).zfill(3)}"
            else:
                new_number = f"INV{timestamp}001"
            
            self.invoice_number = new_number
        
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-issue_date']


class PaymentMethod(models.Model):
    """Saved payment methods for users"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES)
    
    # Card details (encrypted)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    card_exp_month = models.IntegerField(blank=True, null=True)
    card_exp_year = models.IntegerField(blank=True, null=True)
    
    # Mobile money details
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Gateway tokens
    stripe_payment_method_id = models.CharField(max_length=200, blank=True)
    paystack_authorization_code = models.CharField(max_length=200, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.method_type in ['mtn_momo', 'vodafone_cash', 'airteltigo_money']:
            return f"{self.get_method_type_display()} - {self.phone_number}"
        elif self.card_last_four:
            return f"{self.card_brand} ending in {self.card_last_four}"
        return f"{self.get_method_type_display()}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default payment method per user
            PaymentMethod.objects.filter(
                user=self.user, 
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-is_default', '-created_at']