from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    ForgotPasswordRequestView,
    ForgotPasswordConfirmView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),

    path("forgot-password/", ForgotPasswordRequestView.as_view()),
    path("forgot-password/confirm/", ForgotPasswordConfirmView.as_view()),
]