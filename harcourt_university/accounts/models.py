from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from PIL import Image

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('tutor', 'Tutor'),
        ('admin', 'Admin'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.user_type})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path)

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'pk': self.pk})

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_student(self):
        return self.user_type == 'student'

    @property
    def is_tutor(self):
        return self.user_type == 'tutor'


class StudentProfile(models.Model):
    EDUCATION_LEVEL_CHOICES = [
        ('primary', 'Primary School'),
        ('junior_high', 'Junior High School'),
        ('senior_high', 'Senior High School'),
        ('university', 'University'),
        ('professional', 'Professional Development'),
        ('other', 'Other'),
    ]
    
    MODE_CHOICES = [
        ('online', 'Online Only'),
        ('in_person', 'In-Person Only'),
        ('both', 'Both Online & In-Person'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL_CHOICES)
    school_name = models.CharField(max_length=200, blank=True)
    subjects_of_interest = models.TextField(help_text="List subjects you need help with (comma-separated)")
    preferred_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='both')
    budget_range = models.CharField(max_length=50, blank=True, help_text="e.g., GHS 20-50 per hour")
    learning_goals = models.TextField(blank=True, help_text="What do you want to achieve?")
    preferred_language = models.CharField(max_length=50, default='English')
    emergency_contact = models.CharField(max_length=100, blank=True)
    parent_guardian_name = models.CharField(max_length=100, blank=True)
    parent_guardian_phone = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Student Profile"

    def get_subjects_list(self):
        return [subject.strip() for subject in self.subjects_of_interest.split(',') if subject.strip()]


class TutorProfile(models.Model):
    EXPERIENCE_CHOICES = [
        ('0-1', '0-1 years'),
        ('1-3', '1-3 years'),
        ('3-5', '3-5 years'),
        ('5-10', '5-10 years'),
        ('10+', '10+ years'),
    ]

    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='tutor_profile')
    bio = models.TextField(max_length=1000, help_text="Tell students about yourself")
    qualifications = models.TextField(help_text="List your educational qualifications and certifications")
    subjects_offered = models.TextField(help_text="List subjects you can teach (comma-separated)")
    experience = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rate in GHS per hour")
    availability = models.TextField(help_text="Describe your availability (days/times)")
    teaching_mode = models.CharField(max_length=10, choices=StudentProfile.MODE_CHOICES, default='both')
    languages_spoken = models.CharField(max_length=200, default='English')
    
    # Verification documents
    id_document = models.FileField(upload_to='tutor_docs/ids/', blank=True, null=True)
    certifications = models.FileField(upload_to='tutor_docs/certs/', blank=True, null=True)
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')
    verification_notes = models.TextField(blank=True)
    
    # Status and metrics
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    subscription_active = models.BooleanField(default=False)
    subscription_expiry = models.DateTimeField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_sessions = models.IntegerField(default=0)
    total_students = models.IntegerField(default=0)
    response_time = models.IntegerField(default=24, help_text="Average response time in hours")
    
    # Social links
    linkedin_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Tutor Profile"

    @property
    def average_rating(self):
        from tutoring.models import Review
        reviews = Review.objects.filter(tutor=self)
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.0
        return 0.0

    def get_subjects_list(self):
        return [subject.strip() for subject in self.subjects_offered.split(',') if subject.strip()]

    @property
    def is_subscription_active(self):
        if self.subscription_expiry and self.subscription_active:
            return self.subscription_expiry > timezone.now()
        return False

    class Meta:
        ordering = ['-rating', '-created_at']