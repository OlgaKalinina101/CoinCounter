"""
URL configuration for coin_counter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from coin_desk import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhook/', views.webhook_handler, name='webhook'),
    path('webhook2/', views.webhook_handler_2, name='webhook2'),
    path('stats/', views.deal_stats_view, name='deal_stats'),
    path('stats/table/', views.deal_stats_table, name='deal_stats_table'),
    path("dashboard/", include("dashboard.urls")),
]


