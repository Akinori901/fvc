"""apps/chat の URL ルーティング。

config/urls.py から `path("api/chat/", include("apps.chat.presentation.urls"))` で取り込む。
"""

from __future__ import annotations

from django.urls import path

from apps.chat.presentation.views.send_message_view import SendMessageView
from apps.chat.presentation.views.session_views import (
    ChatStatusView,
    SessionDeleteView,
    SessionListView,
    SessionMessagesView,
)

urlpatterns = [
    path("messages/", SendMessageView.as_view(), name="chat-send-message"),
    path("sessions/", SessionListView.as_view(), name="chat-session-list"),
    path(
        "sessions/<int:session_id>/messages/",
        SessionMessagesView.as_view(),
        name="chat-session-messages",
    ),
    path(
        "sessions/<int:session_id>/",
        SessionDeleteView.as_view(),
        name="chat-session-delete",
    ),
    path("status/", ChatStatusView.as_view(), name="chat-status"),
]
