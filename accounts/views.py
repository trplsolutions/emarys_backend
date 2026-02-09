from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer

User = get_user_model()


# -----------------------------
# Signup
# -----------------------------
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "User created successfully", "user": RegisterSerializer(user).data},
            status=status.HTTP_201_CREATED
        )


# -----------------------------
# Login (JWT)
# -----------------------------
class LoginSerializer(TokenObtainPairSerializer):
    # default expects username + password
    # if you want email login, we can customize this later
    pass

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


# -----------------------------
# Forgot Password - Request
# -----------------------------
class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        user = User.objects.filter(email=email).first()
        # Don't reveal if user exists (security)
        if not user:
            return Response({"message": "If that email exists, a reset link was sent."}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # For now: send reset link to console/email backend
        reset_link = f"http://localhost:3000/reset-password?uid={uid}&token={token}"

        send_mail(
            subject="Password Reset",
            message=f"Use this link to reset your password: {reset_link}",
            from_email="no-reply@emarys.com",
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "If that email exists, a reset link was sent."}, status=200)


# -----------------------------
# Forgot Password - Confirm Reset
# -----------------------------
class ForgotPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uid or not token or not new_password:
            return Response({"error": "uid, token, and new_password are required"}, status=400)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({"error": "Invalid uid"}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token"}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password reset successful"}, status=200)