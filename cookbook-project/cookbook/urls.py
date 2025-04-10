"""
URL configuration for cookbook project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include                               # Add 'include'
from django.conf import settings                                    # Add 'settings'
from django.conf.urls.static import static                          # Add 'static'
from rest_framework.routers import DefaultRouter                    # Add 'DefaultRouter'
from recipes import views                                           # Add 'views'

router = DefaultRouter()                                            # Add 'DefaultRouter'
router.register(r'dishes', views.DishViewSet)                       # Add 'DishViewSet'
router.register(r'ingredients', views.IngredientViewSet)            # Add 'IngredientViewSet'
router.register(r'grocery', views.GroceryViewSet)                   # Add 'GroceryViewSet'

urlpatterns = [
    path('admin/', admin.site.urls),                                                            # Connects to your admin
    path('', include('recipes.urls')),                                                          # Connects to your recipes app
    path('api/', include(router.urls)),                                                         # Add 'router.urls'
    path('api-auth/', include('rest_framework.urls')),                                          # Add 'rest_framework.urls'
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)                               # Add 'static' (for media files)
