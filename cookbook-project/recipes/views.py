"""
This file defines the logic for handling HTTP requests in the Django application, both for traditional web views (server-rendered HTML)
and for API endpoints (using Django REST Framework)
"""
from django.db import models
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Dish, Ingredient, Grocery, DishIngredient, Unit
from .serializers import (
    DishSerializer,
    IngredientSerializer,
    GrocerySerializer,
    DishIngredientSerializer,
    UnitSerializer
)

"""
Renders an HTML page listing
"""
def dish_list(
    request,
):
    dishes = Dish.objects.all()
    return render(request, "recipes/list.html", {"dishes": dishes})


"""
These are ModelViewSet classes, which provide CRUD (Create, Read, Update, Delete) operations for models via API endpoints.
"""
class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all().order_by("-id")
    serializer_class = DishSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)  # Allows file uploads

    def create(self, request, *args, **kwargs):
        # Handle both form data and JSON input
        if request.content_type == 'application/json':
            return self.create_from_json(request, *args, **kwargs)
        return super().create(request, *args, **kwargs)

    def create_from_json(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def get_queryset(self):
        """Optional filtering"""
        queryset = super().get_queryset()
        cook_time = self.request.query_params.get("cook_time")
        if cook_time:
            queryset = queryset.filter(cook_time__lte=cook_time)
        return queryset

"""
This class creates an API endpoint for ingredients
"""
class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ["name"]

"""
This class creates an API endpoint for managing grocery objects using Django REST Framework.
"""
class GroceryViewSet(viewsets.ModelViewSet):
    queryset = Grocery.objects.all().order_by("-created_at")
    serializer_class = GrocerySerializer

    """
    1.Retrieves initial queryset of Grocery objects
    2. Filters the queryset based on the "purchased" query parameter, if provided
    3. Returns the filtered queryset
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        purchased = self.request.query_params.get("purchased")
        if purchased in ["true", "false"]:
            queryset = queryset.filter(purchased=purchased == "true")
        return queryset

class DishIngredientViewSet(viewsets.ModelViewSet):
    queryset = DishIngredient.objects.all()
    serializer_class = DishIngredientSerializer

    def get_queryset(self):
        """Filter by dish if provided"""
        queryset = super().get_queryset()
        dish_id = self.request.query_params.get('dish_id')
        if dish_id:
            queryset = queryset.filter(dish_id=dish_id)
        return queryset
    
class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer