from django.urls import path
from . import views
app_name = "accounts"
urlpatterns = [
    
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/<int:pk>/", views.ProfileView.as_view(), name="profile_detail"),
    path("edit-profile/", views.EditProfileView.as_view(), name="edit_profile"),

    # Registration
    path("register/student/", views.StudentRegistrationView.as_view(), name="student_register"),
    path("register/tutor/", views.TutorRegistrationView.as_view(), name="tutor_register"),

    # Tutors
    path("tutors/", views.TutorListView.as_view(), name="tutor_list"),
    # path("tutor/<int:pk>/", views.TutorDetailView.as_view(), name="tutor_detail"),  # Uncomment when ready
]
