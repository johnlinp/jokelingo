"""
URL configuration for jokelingo project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.shortcuts import redirect, render

def language_feed_view(request, source_language_code, target_language_code):
    """View that renders the feed page with language-specific context."""
    canonical_url = request.build_absolute_uri(f'/{source_language_code}/{target_language_code}/')
    
    context = {
        'source_language_code': source_language_code,
        'target_language_code': target_language_code,
        'canonical_url': canonical_url,
    }
    return render(request, 'index.html', context)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('api/v1/', include('feed.urls')),
    path('es/en/', lambda request: language_feed_view(request, 'es', 'en'), name='es_en_index'),
    path('fr/en/', lambda request: language_feed_view(request, 'fr', 'en'), name='fr_en_index'),
    path('', lambda request: redirect('/es/en/', permanent=False), name='root_redirect'),
]
