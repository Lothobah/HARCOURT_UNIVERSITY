
# resources models
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from accounts.models import CustomUser
from tutoring.models import Subject
import os

class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def resource_count(self):
        return self.resource_set.filter(is_approved=True).count()

    class Meta:
        verbose_name_plural = "Resource Categories"
        ordering = ['name']


class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('notes', 'Study Notes'),
        ('past_questions', 'Past Questions'),
        ('assignments', 'Assignments'),
        ('presentations', 'Presentations'),
        ('worksheets', 'Worksheets'),
        ('reference', 'Reference Materials'),
        ('other', 'Other'),
    ]

    LEVEL_CHOICES = [
        ('primary', 'Primary School'),
        ('junior_high', 'Junior High School'),
        ('senior_high', 'Senior High School'),
        ('university', 'University'),
        ('professional', 'Professional'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    category = models.ForeignKey(ResourceCategory, on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_resources')
    
    file = models.FileField(upload_to='resources/%Y/%m/')
    thumbnail = models.ImageField(upload_to='resource_thumbnails/', blank=True, null=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('resources:resource_detail', kwargs={'pk': self.pk})

    @property
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].upper()[1:] if self.file else ''

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    class Meta:
        ordering = ['-created_at']


class VideoLesson(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    tutor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='video_lessons')
    
    # Video source options
    video_file = models.FileField(upload_to='video_lessons/%Y/%m/', blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    vimeo_url = models.URLField(blank=True, null=True)
    
    duration = models.CharField(max_length=20, blank=True, help_text="e.g., 45:30")
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True)
    
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    level = models.CharField(max_length=20, choices=Resource.LEVEL_CHOICES)
    
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    tags = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('resources:video_detail', kwargs={'pk': self.pk})

    @property
    def has_video_source(self):
        return bool(self.video_file or self.youtube_url or self.vimeo_url)

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    class Meta:
        ordering = ['-created_at']


class ResourceDownload(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} downloaded {self.resource.title}"

    class Meta:
        unique_together = ['user', 'resource']
        ordering = ['-downloaded_at']


class VideoView(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    watch_time = models.IntegerField(default=0, help_text="Watch time in seconds")
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} viewed {self.video.title}"

    class Meta:
        unique_together = ['user', 'video']
        ordering = ['-viewed_at']


class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blog_posts')
    content = models.TextField()
    excerpt = models.TextField(max_length=300)
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    meta_description = models.CharField(max_length=160, blank=True)
    
    view_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('resources:blog_detail', kwargs={'slug': self.slug})

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    @property
    def comment_count(self):
        return self.comments.count()

    class Meta:
        ordering = ['-created_at']


class BlogComment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.blog.title}"

    class Meta:
        ordering = ['created_at']