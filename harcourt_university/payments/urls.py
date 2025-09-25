# payments urls
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # Payment listing
    path("", views.PaymentListView.as_view(), name="payment_list"),

    # Pay for tutoring session
    path("session/<int:session_id>/pay/", views.PayForSessionView.as_view(), name="pay_session"),

    # Tutor subscription
    path("subscription/", views.SubscriptionView.as_view(), name="subscription"),

    # Wallet (topup, balance, transactions)
    path("wallet/", views.WalletView.as_view(), name="wallet"),

    # Request refund
    path("refund/<int:payment_id>/", views.RequestRefundView.as_view(), name="request_refund"),

    # Stripe webhook (must not require login)
    path("stripe/webhook/", views.StripeWebhookView.as_view(), name="stripe_webhook"),

    # AJAX check payment status
    path("ajax/check-status/<uuid:payment_id>/", views.ajax_check_payment_status, name="ajax_check_payment_status"),
]
