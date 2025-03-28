from django.urls import path
from . import views

urlpatterns = [
    path('', views.dish_list, name='dish_list'),
]