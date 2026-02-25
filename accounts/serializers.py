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
# Inquiry Serializer (supports file upload)
# ─────────────────────────────────────────────
class InquirySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model  = Inquiry
        fields = (
            "id", "customer", "customer_name", "created_by", "created_by_name",
            "inquiry_type", "status", "priority",
            "subject", "product", "quantity", "terms", "destination", "inquiry_date",
            "description", "notes", "comments",
            "follow_up_date", "follow_up_notes",
            "document", "document_description",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "created_by", "customer_name", "created_by_name")

    def validate_document(self, value):
        if not value:
            return value

        # Validate file size
        if value.size > MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size must not exceed {MAX_DOCUMENT_SIZE_MB}MB."
            )

        # Validate MIME type
        content_type = getattr(value, 'content_type', None)
        if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
            raise serializers.ValidationError(
                "Invalid file type. Allowed: PDF, images (JPG/PNG/WebP), Word documents."
            )

        # Validate file extension as a second layer
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx']
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File extension '{ext}' is not allowed."
            )

        return value

    def create(self, validated_data):
        # Attach the currently logged-in user as creator
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)