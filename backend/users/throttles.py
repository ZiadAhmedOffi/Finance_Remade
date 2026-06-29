from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    scope = "login"


class TokenRefreshRateThrottle(ScopedRateThrottle):
    scope = "token_refresh"


class ApplyAccessRateThrottle(ScopedRateThrottle):
    scope = "apply_access"
