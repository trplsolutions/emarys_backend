from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ForgotPasswordRequestView,
    ForgotPasswordConfirmView,
    CustomerListCreateView,
    CustomerDetailView,
    InquiryListCreateView,
    InquiryDetailView,
    UserListCreateView,
    UserDetailView,
    UserSetPasswordView,
)

urlpatterns = [
    # ── Auth ──────────────────────────────────
    path("auth/register/",                RegisterView.as_view(),              name="register"),
    path("auth/login/",                   LoginView.as_view(),                 name="login"),
    path("auth/logout/",                  LogoutView.as_view(),                name="logout"),
    path("auth/me/",                      MeView.as_view(),                    name="me"),
    path("auth/token/refresh/",           TokenRefreshView.as_view(),          name="token-refresh"),
    path("auth/forgot-password/",         ForgotPasswordRequestView.as_view(), name="forgot-password"),
    path("auth/forgot-password/confirm/", ForgotPasswordConfirmView.as_view(), name="forgot-password-confirm"),

    # ── Customers ─────────────────────────────
    path("customers/",                CustomerListCreateView.as_view(), name="customers-list"),
    path("customers/<int:pk>/",       CustomerDetailView.as_view(),     name="customers-detail"),

    # ── Inquiries ─────────────────────────────
    path("inquiries/",                InquiryListCreateView.as_view(),  name="inquiries-list"),
    path("inquiries/<int:pk>/",       InquiryDetailView.as_view(),      name="inquiries-detail"),

    # ── Users (Admin Only) ────────────────────────
    path("users/",                          UserListCreateView.as_view(),  name="users-list"),
    path("users/<int:pk>/",                 UserDetailView.as_view(),      name="users-detail"),
    path("users/<int:pk>/set-password/",    UserSetPasswordView.as_view(), name="users-set-password"),
]