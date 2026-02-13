from django.urls import path
from . import views

urlpatterns = [
    path('feed', views.FeedView.as_view(), name='feed'),
    path('me/notes', views.MyNotesView.as_view(), name='my_notes'),
    path('posts/<uuid:post_id>/engagement', views.EngagementView.as_view(), name='engagement'),
    path('analytics/events', views.AnalyticsView.as_view(), name='analytics'),
]
