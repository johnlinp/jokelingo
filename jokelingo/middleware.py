"""
Custom middleware for language activation based on target_language_code.
"""
from django.utils import translation


class DisplayLanguageMiddleware:
    """
    Middleware that activates the language based on target_language_code from URL or cookie.
    
    Maps target_language_code to Django language codes:
    - 'en' -> 'en'
    - 'zh-hant' -> 'zh-hant'
    
    This middleware should be placed after LocaleMiddleware so it can override
    the language selection based on the URL pattern or cookie.
    """
    
    # Cookie name for storing preferred display language
    PREFERRED_DISPLAY_LANGUAGE_COOKIE = 'preferred_display_language'
    # Cookie expiration: 1 year in seconds
    COOKIE_MAX_AGE = 31536000
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Mapping from target_language_code to Django language code
        self.language_map = {
            'en': 'en',
            'zh-hant': 'zh-hant',
        }
    
    def __call__(self, request):
        django_language = None
        target_language_code = None
        
        # First, try to extract target_language_code from URL path
        # URL patterns are like: /es/en/, /fr/en/, /ko/en/, /ko/zh-hant/
        path_parts = request.path.strip('/').split('/')
        
        # Check if we have at least 2 parts (source_language_code/target_language_code)
        if len(path_parts) >= 2:
            target_language_code = path_parts[1]
            
            # Map to Django language code if it exists in our mapping
            django_language = self.language_map.get(target_language_code)
        
        # If not found in URL, check cookie
        if not django_language:
            cookie_target_language = request.COOKIES.get(self.PREFERRED_DISPLAY_LANGUAGE_COOKIE)
            if cookie_target_language:
                django_language = self.language_map.get(cookie_target_language)
                if django_language:
                    target_language_code = cookie_target_language
        
        # Activate the language if we found a valid one
        if django_language:
            translation.activate(django_language)
            request.LANGUAGE_CODE = django_language
        
        response = self.get_response(request)
        
        # If we found target_language_code in URL, store it in cookie for future requests
        if target_language_code and target_language_code in self.language_map:
            response.set_cookie(
                self.PREFERRED_DISPLAY_LANGUAGE_COOKIE,
                target_language_code,
                max_age=self.COOKIE_MAX_AGE,
                httponly=False,  # Allow JavaScript to read if needed
                samesite='Lax'
            )
        
        return response
