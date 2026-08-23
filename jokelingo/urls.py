"""
URL configuration for jokelingo project.
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta
from feed.models import Post, PostStatus

SUPPORTED_LANGUAGE_PATHS = {
    '/es/en/': ('es', 'en'),
    '/fr/en/': ('fr', 'en'),
    '/ja/en/': ('ja', 'en'),
    '/ko/en/': ('ko', 'en'),
    '/ja/zh-hant/': ('ja', 'zh-hant'),
    '/ko/zh-hant/': ('ko', 'zh-hant'),
    '/es/zh-hant/': ('es', 'zh-hant'),
}


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
    if preferred_path not in SUPPORTED_LANGUAGE_PATHS:
        preferred_path = '/es/en/'
    
    return redirect(preferred_path, permanent=False)

def login_view(request):
    """View that renders the login page."""
    # If user is already authenticated, redirect to next parameter or root
    if request.user.is_authenticated:
        next_url = request.GET.get('next', '/')
        return redirect(next_url, permanent=False)
    
    # Pass next parameter to template so it can be included in OAuth link
    canonical_url = request.build_absolute_uri('/login/')
    context = {
        'next': request.GET.get('next', ''),
        'canonical_url': canonical_url,
    }
    return render(request, 'login.html', context)

def my_collection_view(request):
    """View that renders the My Collection page."""
    # Check authentication
    if not request.user.is_authenticated:
        # Redirect to login with next parameter
        return redirect('/login/?next=/me/collection/', permanent=False)
    
    canonical_url = request.build_absolute_uri('/me/collection/')
    context = {
        'canonical_url': canonical_url,
    }
    return render(request, 'my_collection.html', context)


def create_post_view(request):
    """Render the secret create-post page for authenticated users."""
    if not request.user.is_authenticated:
        return redirect('/login/?next=/create/', permanent=False)

    minimum_account_age = timedelta(
        days=settings.POST_CREATION_MIN_ACCOUNT_AGE_DAYS
    )
    eligible_at = request.user.created_at + minimum_account_age
    if timezone.now() < eligible_at:
        return render(request, 'create_post_unavailable.html', {
            'eligible_at': eligible_at,
            'minimum_account_age_days': settings.POST_CREATION_MIN_ACCOUNT_AGE_DAYS,
        }, status=403)

    preferred_path = request.COOKIES.get('preferred_language_path', '/es/en/')
    source_language_code, target_language_code = SUPPORTED_LANGUAGE_PATHS.get(
        preferred_path,
        ('es', 'en')
    )

    canonical_url = request.build_absolute_uri('/create/')
    context = {
        'canonical_url': canonical_url,
        'source_language_code': source_language_code,
        'target_language_code': target_language_code,
    }
    return render(request, 'create_post.html', context)


def post_detail_view(request, short_code):
    """Render the canonical, publicly shareable page for one active post."""
    post = get_object_or_404(
        Post,
        short_code=short_code,
        status=PostStatus.ACTIVE,
    )
    canonical_url = request.build_absolute_uri(f'/post/{post.short_code}/')
    response = render(request, 'post_detail.html', {
        'canonical_url': canonical_url,
        'short_code': post.short_code,
    })
    response.set_cookie(
        'preferred_language_path',
        f'/{post.source_language_code}/{post.target_language_code}/',
        max_age=31536000,
    )
    response.set_cookie(
        'preferred_display_language',
        post.target_language_code,
        max_age=31536000,
    )
    return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('api/v1/', include('feed.urls')),
    path('login/', login_view, name='login'),
    path('create/', create_post_view, name='create_post_page'),
    path('me/collection/', my_collection_view, name='my_collection'),
    path('post/<str:short_code>/', post_detail_view, name='post_detail'),
    path('es/en/', lambda request: language_feed_view(request, 'es', 'en'), name='es_en_index'),
    path('fr/en/', lambda request: language_feed_view(request, 'fr', 'en'), name='fr_en_index'),
    path('ja/en/', lambda request: language_feed_view(request, 'ja', 'en'), name='ja_en_index'),
    path('ko/en/', lambda request: language_feed_view(request, 'ko', 'en'), name='ko_en_index'),
    path('ja/zh-hant/', lambda request: language_feed_view(request, 'ja', 'zh-hant'), name='ja_zh_hant_index'),
    path('ko/zh-hant/', lambda request: language_feed_view(request, 'ko', 'zh-hant'), name='ko_zh_hant_index'),
    path('es/zh-hant/', lambda request: language_feed_view(request, 'es', 'zh-hant'), name='es_zh_hant_index'),
    path('', root_redirect_view, name='root_redirect'),
]
