# accounts/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from .models import CustomUser, StudentProfile, TutorProfile
from .forms import StudentRegistrationForm, TutorRegistrationForm, ProfileUpdateForm, StudentProfileForm, TutorProfileForm
from tutoring.models import TutoringSession, Review, TutoringRequest
from resources.models import Resource, VideoLesson
from payments.models import Payment
'''
class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Featured tutors with high ratings
        context['featured_tutors'] = TutorProfile.objects.filter(
            is_approved=True, 
            subscription_active=True
        ).annotate(
            avg_rating=Avg('reviews_received__rating')
        ).order_by('-avg_rating', '-total_sessions')[:6]
        
        # Statistics
        context['stats'] = {
            'total_tutors': TutorProfile.objects.filter(is_approved=True).count(),
            'total_students': CustomUser.objects.filter(user_type='student').count(),
            'total_sessions': TutoringSession.objects.filter(status='completed').count(),
            'total_subjects': 15,  # You can make this dynamic
        }
        
        # Recent success stories or testimonials
        context['recent_reviews'] = Review.objects.filter(
            is_public=True,
            rating__gte=4
        ).select_related('student', 'tutor__user').order_by('-created_at')[:3]
        
        return context
'''

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_student:
            # Student dashboard data
            context['recent_sessions'] = TutoringSession.objects.filter(
                student=user
            ).select_related('tutor', 'subject').order_by('-created_at')[:5]
            
            context['pending_requests'] = TutoringRequest.objects.filter(
                student=user,
                status='pending'
            ).count()
            
            context['upcoming_sessions'] = TutoringSession.objects.filter(
                student=user,
                status__in=['scheduled', 'confirmed'],
                scheduled_date__gt=timezone.now()
            ).order_by('scheduled_date')[:3]
            
            context['total_spent'] = Payment.objects.filter(
                user=user,
                status='completed'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
        elif user.is_tutor:
            # Tutor dashboard data
            context['recent_sessions'] = TutoringSession.objects.filter(
                tutor=user
            ).select_related('student', 'subject').order_by('-created_at')[:5]
            
            context['pending_requests'] = TutoringRequest.objects.filter(
                tutor=user,
                status='pending'
            ).count()
            
            context['upcoming_sessions'] = TutoringSession.objects.filter(
                tutor=user,
                status__in=['scheduled', 'confirmed'],
                scheduled_date__gt=timezone.now()
            ).order_by('scheduled_date')[:3]
            
            # Earnings calculation
            completed_sessions = TutoringSession.objects.filter(
                tutor=user,
                status='completed'
            )
            context['total_earnings'] = sum(session.total_amount for session in completed_sessions)
            context['this_month_earnings'] = sum(
                session.total_amount for session in completed_sessions.filter(
                    scheduled_date__month=timezone.now().month,
                    scheduled_date__year=timezone.now().year
                )
            )
            
            # Recent reviews
            context['recent_reviews'] = Review.objects.filter(
                tutor__user=user
            ).select_related('student').order_by('-created_at')[:3]
            
            # Profile completion check
            try:
                tutor_profile = user.tutor_profile
                context['profile_completion'] = self.calculate_profile_completion(tutor_profile)
            except TutorProfile.DoesNotExist:
                context['profile_completion'] = 0
                
        return context
    
    def calculate_profile_completion(self, profile):
        """Calculate profile completion percentage"""
        fields_to_check = ['bio', 'qualifications', 'subjects_offered', 'experience', 'hourly_rate']
        completed_fields = 0
        
        for field in fields_to_check:
            if getattr(profile, field, None):
                completed_fields += 1
        
        if profile.user.profile_picture:
            completed_fields += 1
            fields_to_check.append('profile_picture')
        
        return int((completed_fields / len(fields_to_check)) * 100)


class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        if 'pk' in self.kwargs:
            return get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        if user.is_tutor:
            # Tutor-specific context
            try:
                tutor_profile = user.tutor_profile
                context['tutor_profile'] = tutor_profile
                context['reviews'] = Review.objects.filter(
                    tutor=tutor_profile,
                    is_public=True
                ).select_related('student').order_by('-created_at')[:10]
                
                context['total_sessions'] = TutoringSession.objects.filter(
                    tutor=user,
                    status='completed'
                ).count()
                
                context['subjects'] = tutor_profile.get_subjects_list()
                
            except TutorProfile.DoesNotExist:
                context['tutor_profile'] = None
                
        elif user.is_student:
            # Student-specific context
            try:
                context['student_profile'] = user.student_profile
            except StudentProfile.DoesNotExist:
                context['student_profile'] = None
                
        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = 'accounts/edit_profile.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_student:
            if hasattr(user, 'student_profile'):
                context['student_form'] = StudentProfileForm(
                    instance=user.student_profile,
                    prefix='student'
                )
            else:
                context['student_form'] = StudentProfileForm(prefix='student')
                
        elif user.is_tutor:
            if hasattr(user, 'tutor_profile'):
                context['tutor_form'] = TutorProfileForm(
                    instance=user.tutor_profile,
                    prefix='tutor'
                )
            else:
                context['tutor_form'] = TutorProfileForm(prefix='tutor')
                
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            form.save()
            
            # Handle profile-specific forms
            if self.object.is_student:
                student_form = StudentProfileForm(
                    request.POST,
                    instance=getattr(self.object, 'student_profile', None),
                    prefix='student'
                )
                if student_form.is_valid():
                    student_profile = student_form.save(commit=False)
                    student_profile.user = self.object
                    student_profile.save()
                    
            elif self.object.is_tutor:
                tutor_form = TutorProfileForm(
                    request.POST,
                    request.FILES,
                    instance=getattr(self.object, 'tutor_profile', None),
                    prefix='tutor'
                )
                if tutor_form.is_valid():
                    tutor_profile = tutor_form.save(commit=False)
                    tutor_profile.user = self.object
                    tutor_profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        
        return self.form_invalid(form)


class StudentRegistrationView(CreateView):
    model = CustomUser
    form_class = StudentRegistrationForm
    template_name = 'registration/student_register.html'
    success_url = reverse_lazy('accounts:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'Welcome to Harcourt University! Your student account has been created.')
        return response


class TutorRegistrationView(CreateView):
    model = CustomUser
    form_class = TutorRegistrationForm
    template_name = 'registration/tutor_register.html'
    success_url = reverse_lazy('accounts:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request, 
            'Welcome to Harcourt University! Your tutor account has been created and is pending approval.'
        )
        return response


class TutorListView(ListView):
    model = TutorProfile
    template_name = 'accounts/tutor_list.html'
    context_object_name = 'tutors'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = TutorProfile.objects.filter(
            is_approved=True,
            verification_status='verified'
        ).select_related('user').annotate(
            avg_rating=Avg('reviews_received__rating'),
            review_count=Count('reviews_received')
        )
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(subjects_offered__icontains=search) |
                Q(bio__icontains=search) |
                Q(qualifications__icontains=search)
            )
        
        # Filter by subject
        subject = self.request.GET.get('subject')
        if subject:
            queryset = queryset.filter(subjects_offered__icontains=subject)
            
        # Filter by experience
        experience = self.request.GET.get('experience')
        if experience:
            queryset = queryset.filter(experience=experience)
            
        # Filter by rate range
        min_rate = self.request.GET.get('min_rate')
        max_rate = self.request.GET.get('max_rate')
        if min_rate:
            queryset = queryset.filter(hourly_rate__gte=min_rate)
        if max_rate:
            queryset = queryset.filter(hourly_rate__lte=max_rate)
            
        # Filter by teaching mode
        mode = self.request.GET.get('mode')
        if mode:
            queryset = queryset.filter(teaching_mode__in=[mode, 'both'])
            
        # Sort
        sort_by = self.request.GET.get('sort', 'rating')
        if sort_by == 'rating':
            queryset = queryset.order_by('-avg_rating', '-review_count')
        elif sort_by == 'price_low':
            queryset = queryset.order_by('hourly_rate')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-hourly_rate')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'experience':
            queryset = queryset.order_by('-experience')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique subjects for filter dropdown
        all_tutors = TutorProfile.objects.filter(is_approved=True)
        subjects = set()
        for tutor in all_tutors:
            subjects.update(tutor.get_subjects_list())
        context['subjects'] = sorted(subjects)
        
        # Experience choices for filter
        context['experience_choices'] = TutorProfile.EXPERIENCE_CHOICES
        
        # Current filter values
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'subject': self.request.GET.get('subject', ''),
            'experience': self.request.GET.get('experience', ''),
            'min_rate': self.request.GET.get('min_rate', ''),
            'max_rate': self.request.GET.get('max_rate', ''),
            'mode': self.request.GET.get('mode', ''),
            'sort': self.request.GET.get('sort', 'rating'),
        }
        
        return context

'''
class TutorDetailView(DetailView):
    model = TutorProfile
    template_name = 'accounts/tutor_detail.html'
    context_object_name = 'tutor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tutor = self.get_object()
        
        # Reviews
        context['reviews'] = Review.objects.filter(
            tutor=tutor,
            is_public=True
        ).select_related('student', 'session').order_by('-created_at')[:10]
        
        # Rating distribution
        ratings = Review.objects.filter(tutor=tutor).values_list('rating', flat=True)
        context['rating_distribution'] = {
            5: ratings.count() if ratings else 0,
            4: list(ratings).count(4) if ratings else 0,
            3: list(ratings).count(3) if ratings else 0,
            2: list(ratings).count(2) if ratings else 0,
            1: list(ratings).count(1) if ratings else 0,
        } if ratings else {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        # Statistics
        context['stats'] = {
            'total_sessions': tutor.total_sessions,
            'total_students': tutor.total_students,
            'avg_rating': tutor.average_rating,
            'review_count': Review.objects.filter(tutor=tutor).count(),
        }
        
        # Subjects as list
        context['subjects'] = tutor.get_subjects_list()
        
        # Similar tutors
        context['similar_tutors'] = TutorProfile.objects.filter(
            is_approved=True,
            verification_status='verified'
        ).exclude(
'''