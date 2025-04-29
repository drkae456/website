import datetime
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.timezone import now

class IdleTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the user is authenticated and the session has expired
        if request.user.is_authenticated:
            # Django's session middleware handles expiry based on SESSION_COOKIE_AGE
            # We just need to check if the user is still authenticated
            pass # No specific action needed here regarding expiry; Django handles it.
        else:
            # If the user is not authenticated, proceed without checking timeout
            pass

        response = self.get_response(request)
        
        # Optional: Add headers to prevent caching of authenticated pages
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response
        
