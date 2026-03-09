from django.urls import path
from . import views

urlpatterns = [
    path('forgot/', views.forgot_password, name='forgot_password'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('reset/', views.reset_password, name='reset_password'),
    path('success/', views.password_success, name='password_success'),
]