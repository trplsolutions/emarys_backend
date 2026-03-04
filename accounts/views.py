from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.db.models import Q

from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Customer, Inquiry
from .serializers import (
    RegisterSerializer, UserSerializer,
    CustomerSerializer, InquirySerializer,
    InquiryListSerializer,
)


User = get_user_model()


# ─────────────────────────────────────────────
# Cookie helpers
# ─────────────────────────────────────────────
def _set_auth_cookies(response, access_token, refresh_token):
    """Set JWT tokens in secure HttpOnly cookies."""
    response.set_cookie(
        key="access_token",
        value=str(access_token),
        httponly=True,
        secure=False,      # Set True in production
        samesite="Lax",
        max_age=3600,
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh_token),
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=86400,
    )


def _delete_auth_cookies(response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


# ═════════════════════════════════════════════
# AUTH VIEWS
# ═════════════════════════════════════════════

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(
            {"message": "Account created successfully.", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("username", "").strip()
        password   = request.data.get("password", "").strip()

        if not identifier or not password:
            return Response(
                {"error": "Email/username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lookup by email OR username
        user_obj = User.objects.filter(Q(email=identifier) | Q(username=identifier)).first()

        if not user_obj:
            return Response(
                {"error": "No account found with these credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=user_obj.username, password=password)

        if not user:
            return Response(
                {"error": "Incorrect password. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        access  = refresh.access_token

        response = Response({
            "message": "Login successful.",
            "user": {
                "id":    user.id,
                "name":  f"{user.first_name} {user.last_name}".strip() or user.username,
                "email": user.email,
                "role":  user.role,
            },
        }, status=status.HTTP_200_OK)

        _set_auth_cookies(response, access, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        _delete_auth_cookies(response)
        return response


class MeView(APIView):
    """Return currently authenticated user's profile (cookie-based)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ─────────────────────────────────────────────
# Forgot Password
# ─────────────────────────────────────────────
class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if user:
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link  = f"http://localhost:3000/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Reset your Emrays password",
                message=f"Click the link to reset your password (expires in 1 hour):\n\n{link}",
                from_email="no-reply@emarys.com",
                recipient_list=[email],
                fail_silently=True,
            )

        # Always return the same message (don't reveal if email exists)
        return Response(
            {"message": "If that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid          = request.data.get("uid", "")
        token        = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not (uid and token and new_password):
            return Response(
                {"error": "uid, token, and new_password are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 9:
            return Response(
                {"error": "Password must be at least 9 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user    = User.objects.get(pk=user_id)
        except Exception:
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)


# ═════════════════════════════════════════════
# CUSTOMER VIEWS
# ═════════════════════════════════════════════

class CustomerListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/customers/         — list all customers
    POST /api/customers/         — upsert customer by email

    Upsert behaviour on POST:
      If a customer with the given email already exists, the existing record is
      returned with HTTP 200.  If not, a new customer is created and returned
      with HTTP 201.  This prevents duplicate-email errors when the same customer
      submits multiple inquiries, and removes the need for a separate lookup call.
    """
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'company_name', 'email']
    ordering_fields    = ['created_at', 'name']
    ordering           = ['-created_at']

    def get_queryset(self):
        return Customer.objects.all()

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower().strip()
        if email:
            existing = Customer.objects.filter(email=email).first()
            if existing:
                # Customer already exists — return the existing record.
                # HTTP 200 (not 201) signals "found, not created".
                return Response(
                    CustomerSerializer(existing).data,
                    status=status.HTTP_200_OK,
                )
        # Customer does not exist — fall through to standard create (returns 201).
        return super().create(request, *args, **kwargs)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/customers/<id>/"""
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.all()


# ═════════════════════════════════════════════
# INQUIRY VIEWS
# ═════════════════════════════════════════════

class InquiryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/inquiries/  — paginated list (lightweight, list-optimised serializer)
    POST /api/inquiries/  — create new inquiry (full serializer with file support)

    Supported query params:
      ?search=<term>           — searches subject, product, customer name/company
      ?status=pending|quoted|confirmed|closed
      ?priority=low|medium|high
      ?ordering=created_at|-created_at|status|priority
    """
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['subject', 'product', 'customer__name', 'customer__company_name']
    ordering_fields    = ['created_at', 'status', 'priority']
    ordering           = ['-created_at']

    def get_queryset(self):
        """
        Build the queryset fresh on every request.
        Applies optional status and priority filters from query params.
        Uses select_related to avoid N+1 queries on customer and created_by.
        """
        qs = Inquiry.objects.select_related('customer', 'created_by').all()

        status_filter   = self.request.query_params.get('status')
        priority_filter = self.request.query_params.get('priority')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if priority_filter:
            qs = qs.filter(priority=priority_filter)

        return qs

    def get_serializer_class(self):
        """
        Use a lightweight read-only serializer for LIST requests.
        Use the full serializer for CREATE (POST) so all fields + file upload work.
        This avoids sending heavy fields (notes, comments, document URL, etc.)
        in the list view where they are not needed.
        """
        if self.request.method == 'GET':
            return InquiryListSerializer
        return InquirySerializer

    def perform_create(self, serializer):
        """Automatically stamp the logged-in user as the inquiry creator."""
        serializer.save(created_by=self.request.user)


class InquiryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/inquiries/<id>/  — full inquiry detail
    PUT    /api/inquiries/<id>/  — full update
    PATCH  /api/inquiries/<id>/  — partial update (e.g. change status only)
    DELETE /api/inquiries/<id>/  — delete inquiry
    """
    serializer_class   = InquirySerializer
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Inquiry.objects.select_related('customer', 'created_by').all()


