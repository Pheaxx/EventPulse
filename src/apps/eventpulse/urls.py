from django.urls import path
from . import views

app_name = "eventpulse"

urlpatterns = [
    path('event/', views.events, name='events'),
    path('relay-settings/', views.RelaySettingsView.as_view(), name="relay-settings-get-post"),
    path('relay-settings/<uuid:relay_id>', views.RelaySettingView.as_view(), name="relay-setting-get-del"),
]
