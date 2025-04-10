"""
This file defines how Django REST Framework converts the model instances into JSON data(serialization)
and vice versa(deserialization).
Basic Structure: Each serializer is a class that inherits from serializers.ModelSerializer.
It automatically generates fields based on the model.
The Meta class inside each serializer specifies which model to use and which fields to include.
"""
from rest_framework import serializers
from .models import (
    Dish,
    Ingredient,
    Grocery,
    CookingStep,
    Unit,
    DishIngredient,
)

class IngredientSerializer(
    serializers.ModelSerializer
):
    class Meta: 
        model = Ingredient
        fields = ["id", "name"]

class CookingStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = CookingStep
        fields = ["id", "step_number", "instruction", "image"]
        extra_kwargs = {"image": {"required": False}}


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "name", "abbreviation"]


class DishIngredientSerializer(serializers.ModelSerializer):
    """
    Uses nested serializers (IngredientSerializer and UnitSerializer) to include full details of related models instead of just IDs.
    """
    ingredient = IngredientSerializer()
    unit = UnitSerializer()

    class Meta:
        model = DishIngredient
        fields = ["id", "ingredient", "quantity", "unit"]


class DishSerializer(
    serializers.ModelSerializer
):
    """
    Parameters:
    1. dishingredient_set is the reverse relation from Dish to DishIngredient, it returns a queryset of DishIngredient objects
    2. many=True indicates that the serializer should expect multiple objects, dish can have a multiple DishIngredient objects and multiple CookingStep objects
    3. read_only=True means that these fields will only be used for serialization.
    """
    dish_ingredients = DishIngredientSerializer(
        source="dishingredient_set", many=True, read_only=True
    )            
    steps = CookingStepSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = Dish
        fields = [
            "id",
            "name",
            "description",
            "dish_ingredients",
            "steps",
            "prep_time",
            "cook_time",
            "image",
        ]
        extra_kwargs = {
            "image": {"required": False}
        }

    """
    This is to include the image URL in the API response, rather than just the image object itself.
    """
    def to_representation(self, instance):
        """Modify image URL in API response"""
        ret = super().to_representation(instance)  
        if instance.image:  
            ret["image"] = instance.image.url  
        else:  
            ret["image"] = None 
        return ret


class GrocerySerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = Grocery
        fields = ["id", "ingredient", "ingredient_name", "purchased", "created_at"]
