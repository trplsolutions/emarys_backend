from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Customer, Inquiry


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    fieldsets     = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone')}),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company_name', 'email', 'phone', 'source', 'created_at')
    list_filter   = ('source',)
    search_fields = ('name', 'company_name', 'email')
    ordering      = ('-created_at',)


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display  = ('subject', 'customer', 'inquiry_type', 'status', 'priority', 'created_by', 'created_at')
    list_filter   = ('status', 'priority', 'inquiry_type')
    search_fields = ('subject', 'product', 'customer__name', 'customer__company_name')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
