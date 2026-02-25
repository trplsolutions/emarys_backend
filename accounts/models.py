from django.contrib.auth.models import AbstractUser
from django.db import models


# ─────────────────────────────────────────────
# Custom User
# ─────────────────────────────────────────────
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin',   'Admin'),
        ('manager', 'Manager'),
        ('sales',   'Sales Person'),
    )
    role  = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales')
    phone = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'auth_user'

    def __str__(self):
        return f"{self.username} ({self.role})"


# ─────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────
class Customer(models.Model):
    SOURCE_CHOICES = (
        ('referral', 'Referral'),
        ('website',  'Website'),
        ('direct',   'Direct'),
        ('other',    'Other'),
    )

    name         = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True, default='')
    email        = models.EmailField(unique=True)
    phone        = models.CharField(max_length=20, blank=True, default='')
    address      = models.TextField(blank=True, default='')
    source       = models.CharField(max_length=20, choices=SOURCE_CHOICES, blank=True, default='')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.company_name})"


# ─────────────────────────────────────────────
# Inquiry
# ─────────────────────────────────────────────
def inquiry_document_path(instance, filename):
    """Save uploaded docs under media/inquiries/<inquiry_id>/"""
    return f"inquiries/{instance.pk or 'new'}/{filename}"


class Inquiry(models.Model):
    STATUS_CHOICES = (
        ('pending',   'Pending'),
        ('quoted',    'Quoted'),
        ('confirmed', 'Confirmed'),
        ('closed',    'Closed'),
    )
    PRIORITY_CHOICES = (
        ('low',    'Low'),
        ('medium', 'Medium'),
        ('high',   'High'),
    )
    TERMS_CHOICES = (
        ('FOB', 'FOB'),
        ('CIF', 'CIF'),
        ('EXW', 'EXW'),
    )
    TYPE_CHOICES = (
        ('product', 'Product Inquiry'),
        ('service', 'Service Inquiry'),
    )

    # Relations
    customer   = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='inquiries')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inquiries')

    # Inquiry info
    inquiry_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='product')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority     = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')

    # Product info
    subject     = models.CharField(max_length=255)
    product     = models.CharField(max_length=255, blank=True, default='')
    quantity    = models.CharField(max_length=100, blank=True, default='')  # varchar to allow "100 pcs"
    terms       = models.CharField(max_length=10, choices=TERMS_CHOICES, blank=True, default='')
    destination = models.CharField(max_length=255, blank=True, default='')
    inquiry_date = models.DateField(null=True, blank=True)

    # Notes
    description     = models.TextField(blank=True, default='')
    notes           = models.TextField(blank=True, default='')
    comments        = models.TextField(blank=True, default='')

    # Follow-up
    follow_up_date  = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True, default='')

    # File attachment (stored in media/inquiries/)
    document        = models.FileField(upload_to=inquiry_document_path, blank=True, null=True)
    document_description = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.customer.name} [{self.status}]"
