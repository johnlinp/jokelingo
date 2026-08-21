from django.urls import path
from . import views

urlpatterns = [
    path('feed', views.FeedView.as_view(), name='feed'),
    path('posts', views.CreatePostView.as_view(), name='create_post'),
    path('posts/by-code/<str:short_code>', views.PostByCodeView.as_view(), name='post_by_code'),
    path('me/collection', views.MyCollectionView.as_view(), name='my_collection'),
    path('posts/<uuid:post_id>/engagement', views.EngagementView.as_view(), name='engagement'),
    path('analytics/events', views.AnalyticsView.as_view(), name='analytics'),
]
