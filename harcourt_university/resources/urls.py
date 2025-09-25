# resources urls
from django.urls import path
from . import views

app_name = "resources"

urlpatterns = [
    # Resource views
    path("", views.ResourceListView.as_view(), name="resource_list"),
    path("resource/<int:pk>/", views.ResourceDetailView.as_view(), name="resource_detail"),
    path("resource/upload/", views.UploadResourceView.as_view(), name="upload_resource"),
    path("resource/<int:pk>/download/", views.download_resource, name="download_resource"),

    # Video lessons
    path("videos/", views.VideoListView.as_view(), name="video_list"),
    path("video/<int:pk>/", views.VideoDetailView.as_view(), name="video_detail"),
    path("video/upload/", views.UploadVideoView.as_view(), name="upload_video"),

    # Blog
    path("blog/", views.BlogListView.as_view(), name="blog_list"),
    path("blog/<int:pk>/", views.BlogDetailView.as_view(), name="blog_detail"),
]
