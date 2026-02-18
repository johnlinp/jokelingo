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
    if preferred_path not in ['/es/en/', '/fr/en/', '/ko/en/', '/ko/zh-hant/']:
        preferred_path = '/es/en/'
    
    return redirect(preferred_path, permanent=False)

def login_view(request):
    """View that renders the login page."""
    # If user is already authenticated, redirect to next parameter or root
    if request.user.is_authenticated:
        next_url = request.GET.get('next', '/')
        return redirect(next_url, permanent=False)
    
    # Pass next parameter to template so it can be included in OAuth link
    context = {
        'next': request.GET.get('next', '')
    }
    return render(request, 'login.html', context)

def my_notes_view(request):
    """View that renders the My Notes page."""
    # Check authentication
    if not request.user.is_authenticated:
        # Redirect to login with next parameter
        return redirect(f'/login/?next=/me/notes/', permanent=False)
    
    return render(request, 'my_notes.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('api/v1/', include('feed.urls')),
    path('login/', login_view, name='login'),
    path('me/notes/', my_notes_view, name='my_notes'),
    path('es/en/', lambda request: language_feed_view(request, 'es', 'en'), name='es_en_index'),
    path('fr/en/', lambda request: language_feed_view(request, 'fr', 'en'), name='fr_en_index'),
    path('ko/en/', lambda request: language_feed_view(request, 'ko', 'en'), name='ko_en_index'),
    path('ko/zh-hant/', lambda request: language_feed_view(request, 'ko', 'zh-hant'), name='ko_zh_hant_index'),
    path('', root_redirect_view, name='root_redirect'),
]
