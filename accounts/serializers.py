import os
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Customer, Inquiry

User = get_user_model()

# ─────────────────────────────────────────────
# Allowed file types for document uploads
# ─────────────────────────────────────────────
ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
MAX_DOCUMENT_SIZE_MB = 5


# ─────────────────────────────────────────────
# User Serializers
# ─────────────────────────────────────────────
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=9)

    class Meta:
        model  = User
        fields = ("id", "username", "email", "password", "first_name", "last_name", "role", "phone")
        extra_kwargs = {
            'first_name': {'required': False, 'default': ''},
            'last_name':  {'required': False, 'default': ''},
            'role':       {'required': False, 'default': 'sales'},
            'phone':      {'required': False, 'default': ''},
        }

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower().strip()

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data.get("role", "sales"),
            phone=validated_data.get("phone", ""),
        )


class UserSerializer(serializers.ModelSerializer):
    """Safe read-only user info, never includes password."""
    class Meta:
        model  = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "phone")
        read_only_fields = fields


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for admin to list, create and update users."""
    password = serializers.CharField(write_only=True, required=False, min_length=9)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "phone", "is_active", "password")

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        # Ignore password here, handled by dedicated endpoint
        validated_data.pop("password", None)
        return super().update(instance, validated_data)


class UserSetPasswordSerializer(serializers.Serializer):
    """Serializer for admin to securely set user password."""
    password = serializers.CharField(write_only=True, min_length=9)


# ─────────────────────────────────────────────
# Customer Serializer
# ─────────────────────────────────────────────
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = ("id", "name", "company_name", "email", "phone", "address", "source", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_email(self, value):
        return value.lower().strip()


# ─────────────────────────────────────────────
# Inquiry Serializer — FULL (used for create / retrieve / update)
# ─────────────────────────────────────────────
class InquirySerializer(serializers.ModelSerializer):
    """
    Full serializer used when creating an inquiry (POST) or viewing
    a single inquiry's detail page (GET /api/inquiries/<id>/).
    Includes every field the backend stores.
    """
    # Read-only convenience fields pulled from related models
    customer_name    = serializers.CharField(source='customer.name',         read_only=True)
    customer_company = serializers.CharField(source='customer.company_name', read_only=True)
    created_by_name  = serializers.CharField(source='created_by.username',   read_only=True)

    class Meta:
        model  = Inquiry
        fields = (
            "id",
            # Relations
            "customer", "customer_name", "customer_company",
            "created_by", "created_by_name",
            # Type / status
            "inquiry_type", "status", "priority",
            # Product info
            "subject", "product", "quantity", "terms", "destination", "inquiry_date",
            # Notes
            "description", "notes", "comments",
            # Follow-up
            "follow_up_date", "follow_up_notes",
            # Document
            "document", "document_description",
            # Timestamps
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_at", "updated_at",
            # created_by is set automatically in the view via perform_create
            "created_by", "created_by_name",
            # Denormalized read-only display fields
            "customer_name", "customer_company",
        )

    def validate_document(self, value):
        """Server-side validation for uploaded file (size + type)."""
        if not value:
            return value

        if value.size > MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size must not exceed {MAX_DOCUMENT_SIZE_MB}MB."
            )

        content_type = getattr(value, 'content_type', None)
        if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
            raise serializers.ValidationError(
                "Invalid file type. Allowed: PDF, images (JPG/PNG/WebP), Word documents."
            )

        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx']
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File extension '{ext}' is not allowed."
            )

        return value

    # NOTE: No custom create() override here.
    # The view's perform_create(serializer) passes created_by=request.user
    # directly to serializer.save(), which is the idiomatic DRF pattern.
    # Having a duplicate create() in the serializer would be redundant.


# ─────────────────────────────────────────────
# Inquiry List Serializer — LIGHTWEIGHT (used for list view only)
# ─────────────────────────────────────────────
class InquiryListSerializer(serializers.ModelSerializer):
    """
    Lightweight read-only serializer used ONLY for GET /api/inquiries/.
    Returns only the fields needed to render a row in the inquiries table.
    Deliberately omits heavy text fields (description, notes, comments,
    follow_up_notes, document_description) to keep the list response small
    and avoid sending data the list view never displays.
    """
    customer_name    = serializers.CharField(source='customer.name',         read_only=True)
    customer_company = serializers.CharField(source='customer.company_name', read_only=True)
    created_by_name  = serializers.CharField(source='created_by.username',   read_only=True, allow_null=True)

    class Meta:
        model  = Inquiry
        fields = (
            "id",
            "customer", "customer_name", "customer_company",
            "created_by", "created_by_name",
            "inquiry_type", "status", "priority",
            "subject", "product", "quantity", "destination",
            "inquiry_date", "follow_up_date",
            "created_at",
        )
        read_only_fields = fields   # list view is always read-only