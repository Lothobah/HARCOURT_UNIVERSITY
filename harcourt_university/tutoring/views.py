# tutoring/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from datetime import datetime, timedelta

from .models import (
    Subject, TutoringRequest, TutoringSession, Review, 
    Message, ForumCategory, ForumPost, ForumReply, Notification
)
from accounts.models import TutorProfile
from .forms import (
    TutoringRequestForm, TutoringSessionForm, ReviewForm,
    MessageForm, ForumPostForm, ForumReplyForm
)


# Dashboard Views
@login_required
def dashboard(request):
    """Main dashboard view"""
    user = request.user
    context = {}
    
    if user.is_student:
        # Student dashboard data
        upcoming_sessions = TutoringSession.objects.filter(
            student=user, 
            scheduled_date__gt=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('scheduled_date')[:5]
        
        recent_requests = TutoringRequest.objects.filter(
            student=user
        ).order_by('-created_at')[:5]
        
        total_sessions = TutoringSession.objects.filter(student=user).count()
        pending_requests = TutoringRequest.objects.filter(
            student=user, status='pending'
        ).count()
        
        context.update({
            'upcoming_sessions': upcoming_sessions,
            'recent_requests': recent_requests,
            'total_sessions': total_sessions,
            'pending_requests': pending_requests,
        })
        
    elif user.is_tutor:
        # Tutor dashboard data
        upcoming_sessions = TutoringSession.objects.filter(
            tutor=user,
            scheduled_date__gt=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('scheduled_date')[:5]
        
        pending_requests = TutoringRequest.objects.filter(
            tutor=user, status='pending'
        ).order_by('-created_at')[:5]
        
        total_sessions = TutoringSession.objects.filter(tutor=user).count()
        total_earnings = TutoringSession.objects.filter(
            tutor=user, status='completed'
        ).aggregate(total=models.Sum('total_amount'))['total'] or 0
        
        avg_rating = Review.objects.filter(
            tutor=user.tutor_profile
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        
        context.update({
            'upcoming_sessions': upcoming_sessions,
            'pending_requests': pending_requests,
            'total_sessions': total_sessions,
            'total_earnings': total_earnings,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        })
    
    # Common data
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False
    ).count()
    
    context.update({
        'unread_notifications': unread_notifications,
    })
    
    return render(request, 'tutoring/dashboard.html', context)


# Subject Views
class SubjectListView(ListView):
    model = Subject
    template_name = 'tutoring/subjects/list.html'
    context_object_name = 'subjects'
    paginate_by = 20
    
    def get_queryset(self):
        return Subject.objects.filter(is_active=True)


# Tutoring Request Views
@login_required
def request_list(request):
    """List tutoring requests"""
    if request.user.is_student:
        requests = TutoringRequest.objects.filter(student=request.user)
    elif request.user.is_tutor:
        # Show requests tutor can handle based on their subjects
        tutor_subjects = request.user.tutor_profile.subjects.all()
        requests = TutoringRequest.objects.filter(
            subject__in=tutor_subjects,
            status='pending'
        ).exclude(student=request.user)
    else:
        requests = TutoringRequest.objects.all()
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)
    
    # Filter by subject
    subject_id = request.GET.get('subject')
    if subject_id:
        requests = requests.filter(subject_id=subject_id)
    
    paginator = Paginator(requests.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'subjects': Subject.objects.filter(is_active=True),
        'current_status': status,
        'current_subject': subject_id,
    }
    return render(request, 'tutoring/requests/list.html', context)


@login_required
def request_create(request):
    """Create a new tutoring request"""
    if not request.user.is_student:
        messages.error(request, "Only students can create tutoring requests.")
        return redirect('tutoring:dashboard')
    
    if request.method == 'POST':
        form = TutoringRequestForm(request.POST)
        if form.is_valid():
            tutoring_request = form.save(commit=False)
            tutoring_request.student = request.user
            tutoring_request.save()
            messages.success(request, "Your tutoring request has been created successfully!")
            return redirect('tutoring:request_detail', pk=tutoring_request.pk)
    else:
        form = TutoringRequestForm()
    
    return render(request, 'tutoring/requests/create.html', {'form': form})


@login_required
def request_detail(request, pk):
    """View tutoring request details"""
    tutoring_request = get_object_or_404(TutoringRequest, pk=pk)
    
    # Check permissions
    if (tutoring_request.student != request.user and 
        not request.user.is_tutor and 
        not request.user.is_staff):
        messages.error(request, "You don't have permission to view this request.")
        return redirect('tutoring:request_list')
    
    context = {
        'request_obj': tutoring_request,
        'can_respond': (request.user.is_tutor and 
                       tutoring_request.status == 'pending' and
                       tutoring_request.student != request.user),
    }
    return render(request, 'tutoring/requests/detail.html', context)


@login_required
@require_http_methods(["POST"])
def request_respond(request, pk):
    """Tutor responds to a tutoring request"""
    if not request.user.is_tutor:
        return JsonResponse({'error': 'Only tutors can respond to requests'}, status=403)
    
    tutoring_request = get_object_or_404(TutoringRequest, pk=pk)
    action = request.POST.get('action')
    
    if action == 'accept':
        tutoring_request.tutor = request.user
        tutoring_request.status = 'accepted'
        tutoring_request.save()
        
        # Create notification
        Notification.objects.create(
            user=tutoring_request.student,
            notification_type='request_accepted',
            title='Request Accepted',
            message=f'Your request "{tutoring_request.title}" has been accepted by {request.user.get_full_name()}',
            action_url=f'/tutoring/requests/{tutoring_request.pk}/'
        )
        
        messages.success(request, "Request accepted successfully!")
    
    elif action == 'reject':
        tutoring_request.status = 'rejected'
        tutoring_request.save()
        messages.info(request, "Request rejected.")
    
    return redirect('tutoring:request_detail', pk=pk)


# Session Views
@login_required
def session_list(request):
    """List tutoring sessions"""
    if request.user.is_student:
        sessions = TutoringSession.objects.filter(student=request.user)
    elif request.user.is_tutor:
        sessions = TutoringSession.objects.filter(tutor=request.user)
    else:
        sessions = TutoringSession.objects.all()
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        sessions = sessions.filter(status=status)
    
    # Filter by upcoming/past
    time_filter = request.GET.get('time')
    if time_filter == 'upcoming':
        sessions = sessions.filter(scheduled_date__gt=timezone.now())
    elif time_filter == 'past':
        sessions = sessions.filter(scheduled_date__lt=timezone.now())
    
    paginator = Paginator(sessions.order_by('-scheduled_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_status': status,
        'current_time': time_filter,
    }
    return render(request, 'tutoring/sessions/list.html', context)


@login_required
def session_create(request):
    """Create a new tutoring session"""
    request_id = request.GET.get('request_id')
    initial_data = {}
    
    if request_id:
        tutoring_request = get_object_or_404(TutoringRequest, pk=request_id)
        if tutoring_request.tutor != request.user and not request.user.is_staff:
            messages.error(request, "You can only create sessions for your accepted requests.")
            return redirect('tutoring:request_list')
        
        initial_data = {
            'student': tutoring_request.student,
            'subject': tutoring_request.subject,
            'title': tutoring_request.title,
            'description': tutoring_request.description,
        }
    
    if request.method == 'POST':
        form = TutoringSessionForm(request.POST, initial=initial_data)
        if form.is_valid():
            session = form.save(commit=False)
            if request.user.is_tutor:
                session.tutor = request.user
            session.save()
            
            # Create notification for student
            Notification.objects.create(
                user=session.student,
                notification_type='session_booked',
                title='Session Scheduled',
                message=f'A tutoring session has been scheduled for {session.scheduled_date.strftime("%Y-%m-%d %H:%M")}',
                action_url=f'/tutoring/sessions/{session.pk}/'
            )
            
            messages.success(request, "Tutoring session created successfully!")
            return redirect('tutoring:session_detail', pk=session.pk)
    else:
        form = TutoringSessionForm(initial=initial_data)
    
    return render(request, 'tutoring/sessions/create.html', {
        'form': form,
        'request_obj': tutoring_request if request_id else None
    })


@login_required
def session_detail(request, pk):
    """View session details"""
    session = get_object_or_404(TutoringSession, pk=pk)
    
    # Check permissions
    if (session.student != request.user and 
        session.tutor != request.user and 
        not request.user.is_staff):
        messages.error(request, "You don't have permission to view this session.")
        return redirect('tutoring:session_list')
    
    context = {
        'session': session,
        'can_start': session.can_start and session.status in ['scheduled', 'confirmed'],
        'can_review': (session.student == request.user and 
                      session.status == 'completed' and 
                      not hasattr(session, 'review')),
    }
    return render(request, 'tutoring/sessions/detail.html', context)


@login_required
@require_http_methods(["POST"])
def session_update_status(request, pk):
    """Update session status"""
    session = get_object_or_404(TutoringSession, pk=pk)
    
    # Check permissions
    if session.tutor != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    action = request.POST.get('action')
    now = timezone.now()
    
    if action == 'start':
        session.status = 'in_progress'
        session.started_at = now
    elif action == 'complete':
        session.status = 'completed'
        session.ended_at = now
    elif action == 'cancel':
        session.status = 'cancelled'
    
    session.save()
    
    return JsonResponse({'status': 'success', 'new_status': session.get_status_display()})


# Review Views
@login_required
def review_create(request, session_pk):
    """Create a review for a completed session"""
    session = get_object_or_404(TutoringSession, pk=session_pk)
    
    if session.student != request.user:
        messages.error(request, "You can only review your own sessions.")
        return redirect('tutoring:session_detail', pk=session_pk)
    
    if session.status != 'completed':
        messages.error(request, "You can only review completed sessions.")
        return redirect('tutoring:session_detail', pk=session_pk)
    
    if hasattr(session, 'review'):
        messages.info(request, "You have already reviewed this session.")
        return redirect('tutoring:session_detail', pk=session_pk)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = request.user
            review.tutor = session.tutor.tutor_profile
            review.session = session
            review.save()
            
            # Create notification for tutor
            Notification.objects.create(
                user=session.tutor,
                notification_type='review_received',
                title='New Review',
                message=f'You received a {review.rating}-star review from {request.user.get_full_name()}',
                action_url=f'/tutoring/sessions/{session.pk}/'
            )
            
            messages.success(request, "Review submitted successfully!")
            return redirect('tutoring:session_detail', pk=session_pk)
    else:
        form = ReviewForm()
    
    return render(request, 'tutoring/reviews/create.html', {
        'form': form,
        'session': session
    })


# Message Views
@login_required
def message_list(request):
    """List messages"""
    inbox = Message.objects.filter(recipient=request.user).order_by('-created_at')
    sent = Message.objects.filter(sender=request.user).order_by('-created_at')
    
    tab = request.GET.get('tab', 'inbox')
    
    if tab == 'sent':
        messages_queryset = sent
    else:
        messages_queryset = inbox
    
    paginator = Paginator(messages_queryset, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_tab': tab,
        'unread_count': inbox.filter(is_read=False).count(),
    }
    return render(request, 'tutoring/messages/list.html', context)


@login_required
def message_detail(request, pk):
    """View message details"""
    message = get_object_or_404(Message, pk=pk)
    
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, "You don't have permission to view this message.")
        return redirect('tutoring:message_list')
    
    # Mark as read if recipient is viewing
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    # Get conversation thread
    thread = Message.objects.filter(
        Q(sender=message.sender, recipient=message.recipient) |
        Q(sender=message.recipient, recipient=message.sender)
    ).order_by('created_at')
    
    context = {
        'message': message,
        'thread': thread,
    }
    return render(request, 'tutoring/messages/detail.html', context)


@login_required
def message_compose(request, recipient_id=None):
    """Compose a new message"""
    initial_data = {}
    recipient = None
    
    if recipient_id:
        recipient = get_object_or_404(User, pk=recipient_id)
        initial_data['recipient'] = recipient
    
    if request.method == 'POST':
        form = MessageForm(request.POST, sender=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            
            # Create notification
            Notification.objects.create(
                user=message.recipient,
                notification_type='message_received',
                title='New Message',
                message=f'You have a new message from {request.user.get_full_name()}',
                action_url=f'/tutoring/messages/{message.pk}/'
            )
            
            messages.success(request, "Message sent successfully!")
            return redirect('tutoring:message_detail', pk=message.pk)
    else:
        form = MessageForm(initial=initial_data, sender=request.user)
    
    return render(request, 'tutoring/messages/compose.html', {
        'form': form,
        'recipient': recipient
    })


# Forum Views
class ForumCategoryListView(ListView):
    model = ForumCategory
    template_name = 'tutoring/forum/categories.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return ForumCategory.objects.filter(is_active=True).annotate(
            post_count=Count('forumpost')
        )


class ForumPostListView(ListView):
    model = ForumPost
    template_name = 'tutoring/forum/posts.html'
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ForumPost.objects.select_related('author', 'category').annotate(
            reply_count=Count('replies')
        )
        
        category_id = self.kwargs.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_id = self.kwargs.get('category_id')
        if category_id:
            context['current_category'] = get_object_or_404(ForumCategory, pk=category_id)
        return context


class ForumPostDetailView(DetailView):
    model = ForumPost
    template_name = 'tutoring/forum/post_detail.html'
    context_object_name = 'post'
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.views += 1
        obj.save(update_fields=['views'])
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['replies'] = self.object.replies.select_related('author').order_by('created_at')
        if self.request.user.is_authenticated:
            context['reply_form'] = ForumReplyForm()
        return context


@login_required
def forum_post_create(request, category_id=None):
    """Create a new forum post"""
    initial_data = {}
    if category_id:
        category = get_object_or_404(ForumCategory, pk=category_id)
        initial_data['category'] = category
    
    if request.method == 'POST':
        form = ForumPostForm(request.POST, initial=initial_data)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Forum post created successfully!")
            return redirect('tutoring:forum_post_detail', pk=post.pk)
    else:
        form = ForumPostForm(initial=initial_data)
    
    return render(request, 'tutoring/forum/post_create.html', {
        'form': form,
        'category': category if category_id else None
    })


@login_required
@require_http_methods(["POST"])
def forum_reply_create(request, post_pk):
    """Create a reply to a forum post"""
    post = get_object_or_404(ForumPost, pk=post_pk)
    
    form = ForumReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.post = post
        reply.author = request.user
        reply.save()
        messages.success(request, "Reply posted successfully!")
    else:
        messages.error(request, "Error posting reply. Please try again.")
    
    return redirect('tutoring:forum_post_detail', pk=post_pk)


# Notification Views
@login_required
def notification_list(request):
    """List user notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read when viewing
    notifications.filter(is_read=False).update(is_read=True)
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tutoring/notifications/list.html', {
        'page_obj': page_obj
    })


@login_required
@require_http_methods(["POST"])
def notification_mark_read(request, pk):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'status': 'success'})


# Search Views
@login_required
def tutor_search(request):
    """Search for tutors"""
    tutors = TutorProfile.objects.filter(is_active=True).select_related('user')
    
    # Filter by subject
    subject_id = request.GET.get('subject')
    if subject_id:
        tutors = tutors.filter(subjects__id=subject_id)
    
    # Filter by experience level
    experience = request.GET.get('experience')
    if experience:
        tutors = tutors.filter(experience_level=experience)
    
    # Filter by rate range
    min_rate = request.GET.get('min_rate')
    max_rate = request.GET.get('max_rate')
    if min_rate:
        tutors = tutors.filter(hourly_rate__gte=min_rate)
    if max_rate:
        tutors = tutors.filter(hourly_rate__lte=max_rate)
    
    # Search by name or bio
    query = request.GET.get('q')
    if query:
        tutors = tutors.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(bio__icontains=query)
        )
    
    # Annotate with average rating
    tutors = tutors.annotate(
        avg_rating=Avg('reviews_received__rating'),
        review_count=Count('reviews_received')
    )
    
    paginator = Paginator(tutors.order_by('-avg_rating'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'subjects': Subject.objects.filter(is_active=True),
        'current_subject': subject_id,
        'current_experience': experience,
        'current_query': query,
        'min_rate': min_rate,
        'max_rate': max_rate,
    }
    return render(request, 'tutoring/tutors/search.html', context)


@login_required
def tutor_profile(request, pk):
    """View tutor profile"""
    tutor = get_object_or_404(TutorProfile, pk=pk)
    
    reviews = Review.objects.filter(tutor=tutor).select_related('student').order_by('-created_at')[:10]
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'tutor': tutor,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'review_count': reviews.count(),
    }
    return render(request, 'tutoring/tutors/profile.html', context)


# API Views for AJAX requests
@login_required
@require_http_methods(["GET"])
def get_notifications_count(request):
    """Get unread notifications count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_http_methods(["GET"])
def session_calendar_data(request):
    """Get session data for calendar view"""
    if request.user.is_student:
        sessions = TutoringSession.objects.filter(student=request.user)
    elif request.user.is_tutor:
        sessions = TutoringSession.objects.filter(tutor=request.user)
    else:
        sessions = TutoringSession.objects.none()
    
    events = []
    for session in sessions:
        events.append({
            'id': session.id,
            'title': session.title,
            'start': session.scheduled_date.isoformat(),
            'end': (session.scheduled_date + timedelta(minutes=session.duration)).isoformat(),
            'url': f'/tutoring/sessions/{session.pk}/',
            'color': '#4f46e5' if session.status == 'confirmed' else '#6b7280'
        })
    
    return JsonResponse(events, safe=False)