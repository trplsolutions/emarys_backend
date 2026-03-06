from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Extends simplejwt's JWTAuthentication to support HttpOnly cookie-based tokens.

    Reading order:
      1. Standard Authorization header  (Bearer <token>) — kept for API clients / Postman
      2. 'access_token' HttpOnly cookie  — used by the Next.js browser frontend

    This allows both browser-based requests (cookie) and direct API access
    (Authorization header) to work with the same authentication setup.
    """

    def authenticate(self, request):
        # 1. Try the standard Authorization header first.
        header = self.get_header(request)

        if header is not None:
            # Standard header path — unchanged from the base class.
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token

        # 2. No Authorization header — try the HttpOnly cookie.
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None  # No credentials at all — let the view decide (AllowAny or 401)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
