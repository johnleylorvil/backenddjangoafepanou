# authentication/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Ajoute des en-têtes de sécurité à toutes les réponses.
    """
    def process_response(self, request, response):
        # Protection contre le clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Protection contre le MIME sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Protection XSS
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Politique de sécurité de contenu (CSP)
        if not settings.DEBUG:
            csp_directives = [
                "default-src 'self'",
                "img-src 'self' data: https:",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",
                "font-src 'self'",
                "connect-src 'self'",
                "frame-ancestors 'none'"
            ]
            response['Content-Security-Policy'] = "; ".join(csp_directives)
        
        # HSTS (HTTP Strict Transport Security)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response