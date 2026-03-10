from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_call_dashboard, name='video_home'),
    path('dashboard/', views.video_call_dashboard, name='video_dashboard'),
    path('room/<str:room_code>/', views.video_room, name='video_room'),
]