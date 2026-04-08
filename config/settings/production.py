from .base import *

# PRODUCTION SPECIFIC SETTINGS

DEBUG = False
ALLOWED_HOSTS = ['*']  # Permitir domínios do Railway

# WhiteNoise for Static Files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

CORS_ALLOWED_ORIGINS = [
    'https://jr-sacoloes-front-production.up.railway.app',
    'http://localhost:5173',
]

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# CSRF & Security (Consistent with Dispatcher project)
CSRF_TRUSTED_ORIGINS = [
    'https://jr-sacoloes-front-production.up.railway.app',
    'https://jr-sacoloes-api-production.up.railway.app'
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security headers (Guide #5)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool) # usually True behind LB
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Throttling
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    "rest_framework.throttling.AnonRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    "anon": "50/hour",
    "user": "500/hour",
}

# Optimized DB Connections
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
}
