from django.urls import path, include
from . import views

app_name = 'tutoring'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Subjects
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    
    # Tutoring Requests
    path('requests/', views.request_list, name='request_list'),
    path('requests/create/', views.request_create, name='request_create'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/respond/', views.request_respond, name='request_respond'),
    
    # Tutoring Sessions
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/update-status/', views.session_update_status, name='session_update_status'),
    path('sessions/calendar-data/', views.session_calendar_data, name='session_calendar_data'),
    
    # Reviews
    path('sessions/<int:session_pk>/review/', views.review_create, name='review_create'),
    
    # Messages
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/compose/', views.message_compose, name='message_compose'),
    path('messages/compose/<int:recipient_id>/', views.message_compose, name='message_compose_to'),
    
    # Forum
    path('forum/', views.ForumCategoryListView.as_view(), name='forum_categories'),
    path('forum/category/<int:category_id>/', views.ForumPostListView.as_view(), name='forum_posts'),
    path('forum/post/create/', views.forum_post_create, name='forum_post_create'),
    path('forum/post/create/<int:category_id>/', views.forum_post_create, name='forum_post_create_category'),
    path('forum/post/<int:pk>/', views.ForumPostDetailView.as_view(), name='forum_post_detail'),
    path('forum/post/<int:post_pk>/reply/', views.forum_reply_create, name='forum_reply_create'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/count/', views.get_notifications_count, name='notifications_count'),
    
    # Tutor Search & Profiles
    path('tutors/', views.tutor_search, name='tutor_search'),
    path('tutors/<int:pk>/', views.tutor_profile, name='tutor_profile'),
]