from django.urls import path
from . import views

urlpatterns = [
    path('feed', views.FeedView.as_view(), name='feed'),
    path('posts/<uuid:post_id>/engagement', views.EngagementView.as_view(), name='engagement'),
    path('analytics/events', views.AnalyticsView.as_view(), name='analytics'),
]
