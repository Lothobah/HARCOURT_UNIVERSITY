# resources/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator
from .models import Resource, VideoLesson, Blog, ResourceCategory, ResourceDownload, VideoView
from .forms import ResourceForm, VideoLessonForm
from tutoring.models import Subject

class ResourceListView(ListView):
    model = Resource
    template_name = 'resources/resource_list.html'
    context_object_name = 'resources'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Resource.objects.filter(is_approved=True).select_related(
            'subject', 'category', 'uploaded_by'
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Filter by subject
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by resource type
        resource_type = self.request.GET.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Filter by level
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by price (free/paid)
        price_filter = self.request.GET.get('price')
        if price_filter == 'free':
            queryset = queryset.filter(is_free=True)
        elif price_filter == 'paid':
            queryset = queryset.filter(is_free=False)
        
        # Sort
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-download_count', '-view_count')
        elif sort_by == 'title':
            queryset = queryset.order_by('title')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter options
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['categories'] = ResourceCategory.objects.filter(is_active=True)
        context['resource_types'] = Resource.RESOURCE_TYPE_CHOICES
        context['levels'] = Resource.LEVEL_CHOICES
        
        # Current filters
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'subject': self.request.GET.get('subject', ''),
            'category': self.request.GET.get('category', ''),
            'type': self.request.GET.get('type', ''),
            'level': self.request.GET.get('level', ''),
            'price': self.request.GET.get('price', ''),
            'sort': self.request.GET.get('sort', 'newest'),
        }
        
        # Featured resources
        context['featured_resources'] = Resource.objects.filter(
            is_approved=True,
            is_featured=True
        ).order_by('-created_at')[:4]
        
        return context


class ResourceDetailView(DetailView):
    model = Resource
    template_name = 'resources/resource_detail.html'
    context_object_name = 'resource'
    
    def get_queryset(self):
        return Resource.objects.filter(is_approved=True).select_related(
            'subject', 'category', 'uploaded_by'
        )
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.view_count += 1
        obj.save()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.get_object()
        
        # Check if user has already downloaded
        if self.request.user.is_authenticated:
            context['already_downloaded'] = ResourceDownload.objects.filter(
                user=self.request.user,
                resource=resource
            ).exists()
        else:
            context['already_downloaded'] = False
        
        # Related resources
        context['related_resources'] = Resource.objects.filter(
            subject=resource.subject,
            is_approved=True
        ).exclude(id=resource.id).order_by('-download_count')[:4]
        
        return context


class UploadResourceView(LoginRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/upload_resource.html'
    success_url = reverse_lazy('resources:resource_list')
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            'Resource uploaded successfully! It will be reviewed before being published.'
        )
        return response


class VideoListView(ListView):
    model = VideoLesson
    template_name = 'resources/video_list.html'
    context_object_name = 'videos'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = VideoLesson.objects.filter(is_approved=True).select_related(
            'subject', 'tutor'
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Filter by subject
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by level
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by price
        price_filter = self.request.GET.get('price')
        if price_filter == 'free':
            queryset = queryset.filter(is_free=True)
        elif price_filter == 'paid':
            queryset = queryset.filter(is_free=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['levels'] = VideoLesson.LEVEL_CHOICES
        
        # Featured videos
        context['featured_videos'] = VideoLesson.objects.filter(
            is_approved=True,
            is_featured=True
        ).order_by('-created_at')[:4]
        
        return context


class VideoDetailView(DetailView):
    model = VideoLesson
    template_name = 'resources/video_detail.html'
    context_object_name = 'video'
    
    def get_queryset(self):
        return VideoLesson.objects.filter(is_approved=True).select_related('subject', 'tutor')
    
    def get_object(self):
        obj = super().get_object()
        
        # Record video view if user is authenticated
        if self.request.user.is_authenticated:
            view, created = VideoView.objects.get_or_create(
                user=self.request.user,
                video=obj
            )
            if created:
                obj.view_count += 1
                obj.save()
        else:
            obj.view_count += 1
            obj.save()
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.get_object()
        
        # Related videos
        context['related_videos'] = VideoLesson.objects.filter(
            subject=video.subject,
            is_approved=True
        ).exclude(id=video.id).order_by('-view_count')[:4]
        
        return context


class UploadVideoView(LoginRequiredMixin, CreateView):
    model = VideoLesson
    form_class = VideoLessonForm
    template_name = 'resources/upload_video.html'
    success_url = reverse_lazy('resources:video_list')
    
    def form_valid(self, form):
        form.instance.tutor = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Video uploaded successfully! It will be reviewed before being published.'
        )
        return response


class BlogListView(ListView):
    model = Blog
    template_name = 'resources/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        return Blog.objects.filter(status='published').select_related('author').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured posts
        context['featured_posts'] = Blog.objects.filter(
            status='published',
            is_featured=True
        ).order_by('-published_at')[:3]
        
        # Recent posts
        context['recent_posts'] = Blog.objects.filter(
            status='published'
        ).order_by('-published_at')[:5]
        
        return context


class BlogDetailView(DetailView):
    model = Blog
    template_name = 'resources/blog_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return Blog.objects.filter(status='published').select_related('author')
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.view_count += 1
        obj.save()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Comments
        context['comments'] = post.comments.filter(is_approved=True).select_related('author').order_by('created_at')
        
        # Related posts
        context['related_posts'] = Blog.objects.filter(
            status='published'
        ).exclude(id=post.id).order_by('-view_count')[:3]
        
        return context


def download_resource(request, pk):
    """Handle resource downloads"""
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to download resources.')
        return redirect('account_login')
    
    resource = get_object_or_404(Resource, pk=pk, is_approved=True)
    
    # Check if resource is free or if user has purchased it
    if not resource.is_free:
        # Check if user has purchased this resource
        from payments.models import Payment
        has_purchased = Payment.objects.filter(
            user=request.user,
            resource=resource,
            status='completed'
        ).exists()
        
        if not has_purchased:
            messages.error(request, 'You need to purchase this resource first.')
            return redirect('resources:resource_detail', pk=pk)
    
    # Record download
    download, created = ResourceDownload.objects.get_or_create(
        user=request.user,
        resource=resource
    )
    
    if created:
        resource.download_count += 1
        resource.save()
    
    # Serve file
    if resource.file:
        response = HttpResponse(resource.file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{resource.file.name}"'
        return response
    
    raise Http404("File not found")