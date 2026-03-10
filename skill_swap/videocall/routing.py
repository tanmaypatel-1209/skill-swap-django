from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # This matches the WebSocket URL in your JavaScript
    re_path(r'ws/call/(?P<room_code>\w+)/$', consumers.VideoCallConsumer.as_asgi()),
]