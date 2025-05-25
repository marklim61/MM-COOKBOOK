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

# Create a custom router that forces /api/ prefix for all endpoints
class APIRootRouter(DefaultRouter):
    def get_api_root_view(self, api_urls=None):
        view = super().get_api_root_view(api_urls=api_urls)
        def wrapped_view(request, *args, **kwargs):
            response = view(request, *args, **kwargs)
            # Ensure all URLs in the response include /api/ prefix
            if response.data:
                for key in response.data:
                    if not response.data[key].startswith('http://127.0.0.1:8000/api/'):
                        response.data[key] = response.data[key].replace(
                            'http://127.0.0.1:8000/',
                            'http://127.0.0.1:8000/api/'
                        )
            return response
        return wrapped_view

router = APIRootRouter()                                          
router.register(r'dishes', views.DishViewSet, basename='dish')
router.register(r'ingredients', views.IngredientViewSet, basename='ingredient')
router.register(r'grocery', views.GroceryViewSet, basename='grocery')
router.register(r'dish-ingredients', views.DishIngredientViewSet, basename='dishingredient')
router.register(r'units', views.UnitViewSet, basename='unit')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),        

    # API Endpoints (all under /api/)  
    path('api/', include(router.urls)),  
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), 

    # HTML Views (separate from API)
    path('dishes/', views.dish_list, name='dish-list'),

    path('', include('recipes.urls')),                                                          # Connects to your recipes app
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)                               # Add 'static' (for media files)
