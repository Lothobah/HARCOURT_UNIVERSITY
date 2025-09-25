# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, StudentProfile, TutorProfile

class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location (City, Region)'})
    )
    
    # Student profile fields
    education_level = forms.ChoiceField(
        choices=StudentProfile.EDUCATION_LEVEL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    school_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School/Institution Name'})
    )
    subjects_of_interest = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List subjects you need help with (comma-separated)'
        }),
        help_text="e.g., Mathematics, Physics, Chemistry"
    )
    preferred_mode = forms.ChoiceField(
        choices=StudentProfile.MODE_CHOICES,
        initial='both',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    budget_range = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., GHS 20-50 per hour'
        })
    )
    learning_goals = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'What do you want to achieve?'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 
                 'location', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.location = self.cleaned_data['location']
        user.user_type = 'student'
        
        if commit:
            user.save()
            
            # Create student profile
            StudentProfile.objects.create(
                user=user,
                education_level=self.cleaned_data['education_level'],
                school_name=self.cleaned_data['school_name'],
                subjects_of_interest=self.cleaned_data['subjects_of_interest'],
                preferred_mode=self.cleaned_data['preferred_mode'],
                budget_range=self.cleaned_data['budget_range'],
                learning_goals=self.cleaned_data['learning_goals'],
            )
        
        return user


class TutorRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    location = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location (City, Region)'})
    )
    
    # Tutor profile fields
    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Tell students about yourself and your teaching approach'
        }),
        max_length=1000
    )
    qualifications = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List your educational qualifications and certifications'
        })
    )
    subjects_offered = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List subjects you can teach (comma-separated)'
        })
    )
    experience = forms.ChoiceField(
        choices=TutorProfile.EXPERIENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    hourly_rate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your hourly rate in GHS',
            'step': '0.01'
        })
    )
    availability = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Describe your availability (days/times)'
        })
    )
    teaching_mode = forms.ChoiceField(
        choices=StudentProfile.MODE_CHOICES,
        initial='both',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    languages_spoken = forms.CharField(
        max_length=200,
        initial='English',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Languages you can teach in'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 
                 'location', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_hourly_rate(self):
        rate = self.cleaned_data.get('hourly_rate')
        if rate and rate <= 0:
            raise ValidationError("Hourly rate must be greater than 0.")
        return rate

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.location = self.cleaned_data['location']
        user.user_type = 'tutor'
        
        if commit:
            user.save()
            
            # Create tutor profile
            TutorProfile.objects.create(
                user=user,
                bio=self.cleaned_data['bio'],
                qualifications=self.cleaned_data['qualifications'],
                subjects_offered=self.cleaned_data['subjects_offered'],
                experience=self.cleaned_data['experience'],
                hourly_rate=self.cleaned_data['hourly_rate'],
                availability=self.cleaned_data['availability'],
                teaching_mode=self.cleaned_data['teaching_mode'],
                languages_spoken=self.cleaned_data['languages_spoken'],
            )
        
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'location', 'profile_picture', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['education_level', 'school_name', 'subjects_of_interest', 
                 'preferred_mode', 'budget_range', 'learning_goals', 
                 'emergency_contact', 'parent_guardian_name', 'parent_guardian_phone']
        widgets = {
            'education_level': forms.Select(attrs={'class': 'form-control'}),
            'school_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subjects_of_interest': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preferred_mode': forms.Select(attrs={'class': 'form-control'}),
            'budget_range': forms.TextInput(attrs={'class': 'form-control'}),
            'learning_goals': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_guardian_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_guardian_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TutorProfileForm(forms.ModelForm):
    class Meta:
        model = TutorProfile
        fields = ['bio', 'qualifications', 'subjects_offered', 'experience', 
                 'hourly_rate', 'availability', 'teaching_mode', 'languages_spoken',
                 'id_document', 'certifications', 'linkedin_url', 'website_url']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subjects_offered': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'experience': forms.Select(attrs={'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'teaching_mode': forms.Select(attrs={'class': 'form-control'}),
            'languages_spoken': forms.TextInput(attrs={'class': 'form-control'}),
            'id_document': forms.FileInput(attrs={'class': 'form-control'}),
            'certifications': forms.FileInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'website_url': forms.URLInput(attrs={'class': 'form-control'}),
        }