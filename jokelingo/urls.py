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
    response = render(request, 'index.html', context)
    
    # Store the language choice in a cookie (expires in 1 year)
    language_path = f'/{source_language_code}/{target_language_code}/'
    response.set_cookie('preferred_language_path', language_path, max_age=31536000)  # 1 year
    
    return response

def root_redirect_view(request):
    """Redirect root path based on cookie preference, defaulting to /es/en/"""
    preferred_path = request.COOKIES.get('preferred_language_path', '/es/en/')
    
    # Validate that the preferred path is one of our valid language paths
    if preferred_path not in ['/es/en/', '/fr/en/']:
        preferred_path = '/es/en/'
    
    return redirect(preferred_path, permanent=False)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('api/v1/', include('feed.urls')),
    path('es/en/', lambda request: language_feed_view(request, 'es', 'en'), name='es_en_index'),
    path('fr/en/', lambda request: language_feed_view(request, 'fr', 'en'), name='fr_en_index'),
    path('', root_redirect_view, name='root_redirect'),
]
