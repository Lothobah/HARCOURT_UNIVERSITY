# tutoring/models.py
from django.db import models
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser, TutorProfile

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class TutoringRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low - More than a week'),
        ('medium', 'Medium - Within a week'),
        ('high', 'High - Within 24 hours'),
        ('urgent', 'Urgent - ASAP'),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tutoring_requests')
    tutor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_requests', blank=True, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Describe what you need help with")
    level = models.CharField(max_length=20, choices=TutorProfile.EXPERIENCE_CHOICES)
    preferred_mode = models.CharField(max_length=10, choices=[('online', 'Online'), ('in_person', 'In Person'), ('both', 'Either')])
    budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Budget per hour in GHS")
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.student.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tutoring:request_detail', kwargs={'pk': self.pk})

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at if self.expires_at else False

    class Meta:
        ordering = ['-created_at']


class TutoringSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]

    DURATION_CHOICES = [
        (30, '30 minutes'),
        (60, '1 hour'),
        (90, '1.5 hours'),
        (120, '2 hours'),
        (180, '3 hours'),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='student_sessions')
    tutor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tutor_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    request = models.ForeignKey(TutoringRequest, on_delete=models.CASCADE, blank=True, null=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateTimeField()
    duration = models.IntegerField(choices=DURATION_CHOICES, default=60)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Meeting details
    mode = models.CharField(max_length=10, choices=[('online', 'Online'), ('in_person', 'In Person')])
    meeting_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    location = models.TextField(blank=True, help_text="Physical location if in-person")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, help_text="Session notes and outcomes")
    homework_assigned = models.TextField(blank=True)
    materials_needed = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.student.get_full_name()} with {self.tutor.get_full_name()}"

    def save(self, *args, **kwargs):
        self.total_amount = self.rate * (self.duration / 60)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tutoring:session_detail', kwargs={'pk': self.pk})

    @property
    def is_upcoming(self):
        return self.scheduled_date > timezone.now() and self.status in ['scheduled', 'confirmed']

    @property
    def can_start(self):
        time_until = self.scheduled_date - timezone.now()
        return time_until.total_seconds() <= 900  # 15 minutes before

    class Meta:
        ordering = ['scheduled_date']


class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_given')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='reviews_received')
    session = models.OneToOneField(TutoringSession, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    would_recommend = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.student.get_full_name()} for {self.tutor.user.get_full_name()}"

    class Meta:
        ordering = ['-created_at']


class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} to {self.recipient.get_full_name()}"

    class Meta:
        ordering = ['-created_at']


class ForumCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#663399')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def post_count(self):
        return self.forumpost_set.count()

    class Meta:
        verbose_name_plural = "Forum Categories"
        ordering = ['name']


class ForumPost(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_solved = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tutoring:forum_post_detail', kwargs={'pk': self.pk})

    @property
    def reply_count(self):
        return self.replies.count()

    class Meta:
        ordering = ['-is_pinned', '-created_at']


class ForumReply(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    parent_reply = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to {self.post.title} by {self.author.get_full_name()}"

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = "Forum Replies"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('session_booked', 'Session Booked'),
        ('session_cancelled', 'Session Cancelled'),
        ('session_reminder', 'Session Reminder'),
        ('request_received', 'Request Received'),
        ('request_accepted', 'Request Accepted'),
        ('review_received', 'Review Received'),
        ('message_received', 'Message Received'),
        ('payment_successful', 'Payment Successful'),
        ('subscription_expiry', 'Subscription Expiry'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.get_full_name()}: {self.title}"

    class Meta:
        ordering = ['-created_at']
