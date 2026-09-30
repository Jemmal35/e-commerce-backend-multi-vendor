from django.urls import path

from .views import UserRegistrationView, UserProfileView, ChangePasswordView, LogoutView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name= 'user-registration'),
    path('auth/login/', TokenObtainPairView.as_view(), name= 'token_obtain_pair'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name= 'token_refresh'),
    path('auth/user/profile/', UserProfileView.as_view(), name= 'user-profile'),
    path('auth/change-password/',ChangePasswordView.as_view(), name='change-password'),
    path('auth/logout/', LogoutView.as_view(), name= 'user-logout')
]
