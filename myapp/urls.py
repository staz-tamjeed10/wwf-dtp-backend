from django.urls import path
from .views import (
    RegisterAPI,
    VerifyEmailAPI,
    login_api,
    logout_api,
    profile_api,
    update_profile_api,
    change_password_api,
    password_reset_api,
    password_reset_confirm_api
)

urlpatterns = [
    path('register/', RegisterAPI.as_view(), name='api_register'),
    path('verify-email/<str:token>/', VerifyEmailAPI.as_view(), name='verify-email'),
    path('login/', login_api, name='api_login'),
    path('logout/', logout_api, name='api_logout'),
    path('profile/', profile_api, name='api_profile'),
    path('profile/update/', update_profile_api, name='api_update_profile'),
    path('change-password/', change_password_api, name='api_change_password'),
    path('password-reset/', password_reset_api, name='api_password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/',
         password_reset_confirm_api,
         name='api_password_reset_confirm'),
]