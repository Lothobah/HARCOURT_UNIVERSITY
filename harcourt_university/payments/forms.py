from django import forms
from .models import Refund

class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = Refund
        fields = ['reason', 'reason_detail', 'amount']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'reason_detail': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please explain why you are requesting a refund'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Refund amount (leave blank for full refund)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount'].required = False


class PaymentMethodForm(forms.Form):
    PAYMENT_CHOICES = [
        ('stripe', 'Credit/Debit Card'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('vodafone_cash', 'Vodafone Cash'),
        ('airteltigo_money', 'AirtelTigo Money'),
        ('wallet', 'Wallet Balance'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='stripe'
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 0244123456'
        })
    )
    
    save_payment_method = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        
        if payment_method in ['mtn_momo', 'vodafone_cash', 'airteltigo_money'] and not phone_number:
            raise forms.ValidationError("Phone number is required for mobile money payments.")
        
        return cleaned_data


class WalletTopUpForm(forms.Form):
    AMOUNT_CHOICES = [
        ('10', 'GHS 10'),
        ('20', 'GHS 20'),
        ('50', 'GHS 50'),
        ('100', 'GHS 100'),
        ('200', 'GHS 200'),
        ('custom', 'Custom Amount'),
    ]
    
    amount_choice = forms.ChoiceField(
        choices=AMOUNT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='50'
    )
    
    custom_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '5',
            'placeholder': 'Enter amount'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('stripe', 'Credit/Debit Card'),
            ('mtn_momo', 'MTN Mobile Money'),
            ('vodafone_cash', 'Vodafone Cash'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='stripe'
    )

    def clean(self):
        cleaned_data = super().clean()
        amount_choice = cleaned_data.get('amount_choice')
        custom_amount = cleaned_data.get('custom_amount')
        
        if amount_choice == 'custom' and not custom_amount:
            raise forms.ValidationError("Please enter a custom amount.")
        
        if custom_amount and custom_amount < 5:
            raise forms.ValidationError("Minimum top-up amount is GHS 5.")
        
        return cleaned_data

    def get_amount(self):
        """Get the final amount to be charged"""
        amount_choice = self.cleaned_data.get('amount_choice')
        
        if amount_choice == 'custom':
            return self.cleaned_data.get('custom_amount', 0)
        else:
            return float(amount_choice)

'''
# Search and Filter Forms
class TutorSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search tutors by name, subject, or keywords'
        })
    )
    
    subject = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    
    experience = forms.ChoiceField(
        choices=[('', 'Any Experience')] + list(TutorProfile.EXPERIENCE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    min_rate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min rate',
            'step': '0.01'
        })
    )
    
    max_rate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max rate',
            'step': '0.01'
        })
    )
    
    mode = forms.ChoiceField(
        choices=[('', 'Any Mode')] + list(StudentProfile.MODE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('rating', 'Highest Rated'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('newest', 'Newest'),
            ('experience', 'Most Experienced'),
        ],
        initial='rating',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ResourceSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search resources'
        })
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        empty_label="All Subjects",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=ResourceCategory.objects.filter(is_active=True),
        empty_label="All Categories",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    resource_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Resource.RESOURCE_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(Resource.LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    price = forms.ChoiceField(
        choices=[
            ('', 'All Resources'),
            ('free', 'Free Only'),
            ('paid', 'Paid Only'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('newest', 'Newest'),
            ('oldest', 'Oldest'),
            ('popular', 'Most Popular'),
            ('title', 'Title A-Z'),
        ],
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
'''