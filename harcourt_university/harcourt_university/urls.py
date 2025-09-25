# harcourt_university/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
    path('admin/', admin.site.urls),

    # App routes
    path("", views.HomeView.as_view(), name="home"),
    path('accounts/', include('accounts.urls')),   
    path('payments/', include('payments.urls')),   
    path('resources/', include('resources.urls')), 
    path('tutoring/', include('tutoring.urls')), 
]

# Media files for user uploads
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
