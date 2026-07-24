"""
Project-wide security response headers.

The React SPA gets a strict Content-Security-Policy from nginx (frontend/nginx.conf).
This middleware covers the surfaces nginx proxies straight to Django — the admin and
the DRF browsable API — which would otherwise ship no CSP at all (EF-03). The script
policy keeps 'unsafe-inline' because the Django admin relies on inline scripts/styles;
the value is in the framing, base-uri, and object restrictions that shrink the blast
radius of any injected markup. The bearer tokens the SPA holds never reach these
pages, so the looser script policy here does not widen the app's real exposure.
"""

CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Content-Security-Policy', CSP)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        return response
