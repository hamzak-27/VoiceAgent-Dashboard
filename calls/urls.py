from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('call-details/<int:call_id>/', views.get_call_details, name='call_details'),
    path('webhook/', views.webhook, name='webhook'),
    path('latest-calls/', views.latest_calls, name='latest_calls'),
]