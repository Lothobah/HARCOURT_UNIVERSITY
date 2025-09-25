# tutoring/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

from .models import (
    TutoringRequest, TutoringSession, Review, Message, 
    ForumPost, ForumReply, Subject
)
from accounts.models import TutorProfile

User = get_user_model()


class TutoringRequestForm(forms.ModelForm):
    class Meta:
        model = TutoringRequest
        fields = [
            'subject', 'title', 'description', 'level', 'preferred_mode',
            'budget', 'urgency', 'location', 'deadline'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What do you need help with?'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide details about what you need help with...'
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'preferred_mode': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Budget per hour (GHS)',
                'min': '0',
                'step': '0.01'
            }),
            'urgency': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location (if in-person)'
            }),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline <= timezone.now():
            raise ValidationError("Deadline must be in the future.")
        return deadline

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget <= 0:
            raise ValidationError("Budget must be greater than 0.")
        return budget


class TutoringSessionForm(forms.ModelForm):
    class Meta:
        model = TutoringSession
        fields = [
            'student', 'subject', 'title', 'description', 'scheduled_date',
            'duration', 'rate', 'mode', 'meeting_link', 'meeting_id',
            'meeting_password', 'location', 'materials_needed'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Session title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Session description...'
            }),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration': forms.Select(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hourly rate (GHS)',
                'min': '0',
                'step': '0.01'
            }),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meeting link (for online sessions)'
            }),
            'meeting_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meeting ID'
            }),
            'meeting_password': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meeting password'
            }),
            'location': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Physical location (for in-person sessions)'
            }),
            'materials_needed': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Materials needed for the session...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter students to only show active students
        self.fields['student'].queryset = User.objects.filter(
            is_active=True, is_student=True
        ).order_by('first_name', 'last_name')

    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if scheduled_date and scheduled_date <= timezone.now():
            raise ValidationError("Session must be scheduled for the future.")
        return scheduled_date

    def clean_rate(self):
        rate = self.cleaned_data.get('rate')
        if rate is not None and rate <= 0:
            raise ValidationError("Rate must be greater than 0.")
        return rate

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        meeting_link = cleaned_data.get('meeting_link')
        location = cleaned_data.get('location')

        if mode == 'online' and not meeting_link:
            raise ValidationError("Meeting link is required for online sessions.")
        
        if mode == 'in_person' and not location:
            raise ValidationError("Location is required for in-person sessions.")

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment', 'would_recommend', 'is_public']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this tutor...'
            }),
            'would_recommend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        if comment and len(comment.strip()) < 10:
            raise ValidationError("Please provide a more detailed comment (at least 10 characters).")
        return comment


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content']
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Message subject'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Type your message here...'
            }),
        }

    def __init__(self, *args, **kwargs):
        sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)
        
        if sender:
            # Exclude the sender from recipient choices
            self.fields['recipient'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk=sender.pk).order_by('first_name', 'last_name')

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 5:
            raise ValidationError("Message content is too short.")
        return content


class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ['category', 'title', 'content']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Post title'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Write your post content here...'
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 5:
            raise ValidationError("Title must be at least 5 characters long.")
        return title

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 20:
            raise ValidationError("Post content must be at least 20 characters long.")
        return content


class ForumReplyForm(forms.ModelForm):
    class Meta:
        model = ForumReply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your reply here...'
            }),
        }

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 5:
            raise ValidationError("Reply must be at least 5 characters long.")
        return content


class TutorSearchForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    experience_level = forms.ChoiceField(
        choices=[('', 'Any Experience')] + TutorProfile.EXPERIENCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    min_rate = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min rate (GHS)',
            'step': '0.01'
        })
    )
    
    max_rate = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max rate (GHS)',
            'step': '0.01'
        })
    )
    
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or keywords...'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        min_rate = cleaned_data.get('min_rate')
        max_rate = cleaned_data.get('max_rate')

        if min_rate and max_rate and min_rate > max_rate:
            raise ValidationError("Minimum rate cannot be greater than maximum rate.")

        return cleaned_data


class SessionFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TIME_CHOICES = [
        ('', 'All Time'),
        ('upcoming', 'Upcoming'),
        ('past', 'Past'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    time_filter = forms.ChoiceField(
        choices=TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class RequestFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    urgency = forms.ChoiceField(
        choices=[('', 'All Urgency Levels')] + TutoringRequest.URGENCY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )