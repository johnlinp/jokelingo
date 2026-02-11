"""
URL configuration for jokelingo project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('api/v1/', include('feed.urls')),
    path('es/en/', TemplateView.as_view(template_name='index.html'), name='index'),
    path('', lambda request: redirect('/es/en/', permanent=False), name='root_redirect'),
]
