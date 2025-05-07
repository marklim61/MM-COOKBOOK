"""
This file defines how Django REST Framework converts the model instances into JSON data(serialization)
and vice versa(deserialization).
Basic Structure: Each serializer is a class that inherits from serializers.ModelSerializer.
It automatically generates fields based on the model.
The Meta class inside each serializer specifies which model to use and which fields to include.
"""
from django.db import models
from django.db import transaction  # Add this import
from rest_framework import serializers
from .models import (
    Dish,
    Ingredient,
    Grocery,
    CookingStep,
    Unit,
    DishIngredient,
)
import inflect                          # For plural/singular handling

p = inflect.engine()

class IngredientSerializer(serializers.ModelSerializer):
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
    ingredient = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), required=False
    )
    ingredient_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    ingredient_detail = IngredientSerializer(source="ingredient", read_only=True)

    unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), required=False
    )
    unit_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    unit_detail = UnitSerializer(source="unit", read_only=True)

    class Meta:
        model = DishIngredient
        fields = [
            "id",
            "ingredient",
            "ingredient_name",
            "ingredient_detail",
            "quantity",
            "unit",
            "unit_name",
            "unit_detail",
        ]

    """
    Convert to singular form and lowercase
    Two different algorithms for ingredient and unit
    1. Ingredient: Have more irregular plural forms. p.singular_noun() is more sophisticated solution that handles irregularities
    2. Unit: Units are more regular. Just remove the last 's' if it exists.
    """
    def normalize_name(self, name, is_ingredient=False, is_unit=False):
        name = name.strip().lower()
        if is_ingredient:
            return p.singular_noun(name) or name
        if is_unit:
            # Handle common unit plurals (cups → cup, grams → gram)
            if name.endswith('s') and len(name) > 1:
                return name[:-1]
            return name
        return name

    """
    Validates the ingredient and unit data in the provided dictionary.
    For ingredients:
    - It attempts to match the provided ingredient name with existing ingredients,
      considering both singular and plural forms.
    - If a match is found, it raises a ValidationError, suggesting the use of the existing ingredient.
    For units:
    - It checks the unit name against existing units, considering both singular and plural forms,
      as well as abbreviations up to the first three characters.
    - If a match is found, it raises a ValidationError with details of the existing unit.
    Returns:
        The normalized data dictionary if no conflicts are found.
    """
    def validate(self, data):
        # INGREDIENT VALIDATION
        if 'ingredient_name' in data:
            norm_name = self.normalize_name(data['ingredient_name'], is_ingredient=True)            # Its's true because we're validating an ingredient
            """
            conflict is a variable that stores the result of the database query. It can hold one of two values:
            1. An Ingredient object: if a matching ingredient is found in the database, conflict 
            will be an instance of the Ingredient model, representing the conflicting ingredient.
            2. None: if no matching ingredient is found in the database, conflict will be None.
            """
            conflict = Ingredient.objects.filter(                  # Conflict is a variable that stores the result of the database query
                # Q stands for Query. models.Q is a way to create object that can be used to filter database queries.
                # It's a way to build a query using a more Pythonic syntax, rather than writing raw SQL
                models.Q(name__iexact=norm_name) |                                                                                  
                models.Q(name__iexact=p.plural(norm_name))         # Check if there's an ingredient with the plural form of the name               
            ).first()   # When using filter() or get() to retrieve objects from the DB, first() is a way to retrieve only the first object from the QuerySet
            if conflict:
                raise serializers.ValidationError({
                    'ingredient_name': f'Use existing "{conflict.name}" (ID: {conflict.id}) instead'
                })
            data['ingredient_name'] = norm_name                     # Update the ingredient name which should be singular

        # UNIT VALIDATION
        if 'unit_name' in data:
            norm_unit = self.normalize_name(data['unit_name'], is_unit=True)
            
            # Check against both name and abbreviation in singular/plural forms
            conflict = Unit.objects.filter(
                models.Q(name__iexact=norm_unit) |
                models.Q(name__iexact=norm_unit + 's') |  # Check plural version
                models.Q(abbreviation__iexact=norm_unit[:3]) |
                models.Q(abbreviation__iexact=(norm_unit + 's')[:3])
            ).first()
            
            if conflict:
                raise serializers.ValidationError({
                    'unit_name': (
                        f'Unit conflict: "{data["unit_name"]} matches '
                        f'existing "{conflict.name}" (ID: {conflict.id}, '
                        f'Abbr: {conflict.abbreviation})'
                    )
                })
            data['unit_name'] = norm_unit  # Store normalized name

        return data

    def create(self, validated_data):
        # Handle Ingredient
        if 'ingredient_name' in validated_data:
            norm_name = validated_data.pop('ingredient_name')
            ingredient, created = Ingredient.objects.get_or_create(
                name__iexact=norm_name,
                defaults={'name': norm_name.capitalize()}
            )
            if not created and ingredient.name != norm_name.capitalize():
                # Handle case where plural exists but singular doesn't
                ingredient = Ingredient.objects.create(name=norm_name.capitalize())
            validated_data['ingredient'] = ingredient

        # Handle Unit
        if 'unit_name' in validated_data:
            norm_unit = validated_data.pop('unit_name')
            
            # Final check with lock to prevent race conditions
            with transaction.atomic():
                conflict = Unit.objects.select_for_update().filter(
                    models.Q(name__iexact=norm_unit) |
                    models.Q(name__iexact=norm_unit + 's') |
                    models.Q(abbreviation__iexact=norm_unit[:3])
                ).first()
                
                if conflict:
                    raise serializers.ValidationError({
                        'unit_name': f'Unit was just created: {conflict.name}'
                    })
                
                unit = Unit.objects.create(
                    name=norm_unit.capitalize(),
                    abbreviation=norm_unit[:3]
                )
                validated_data['unit'] = unit

        return super().create(validated_data)

class DishSerializer(serializers.ModelSerializer):
    """
    Parameters:
    1. dishingredient_set is the reverse relation from Dish to DishIngredient, it returns a queryset of DishIngredient objects
    2. many=True indicates that the serializer should expect multiple objects, dish can have a multiple DishIngredient objects and multiple CookingStep objects
    3. read_only=True means that these fields will only be used for serialization.
    """
    dish_ingredients = DishIngredientSerializer(
        source="dishingredient_set", many=True, required=False
    )
    steps = CookingStepSerializer(many=True, read_only=True)

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
        extra_kwargs = {"image": {"required": False}}

    def create(self, validated_data):
        ingredients_data = validated_data.pop("dishingredient_set", [])
        dish = Dish.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            # Handle ingredient
            if "ingredient_name" in ingredient_data:
                ingredient, _ = Ingredient.objects.get_or_create(
                    name=ingredient_data.pop("ingredient_name")
                )
                ingredient_data["ingredient"] = ingredient

            # Handle unit
            if "unit_name" in ingredient_data:
                unit, _ = Unit.objects.get_or_create(
                    name=ingredient_data.pop("unit_name")
                )
                ingredient_data["unit"] = unit

            DishIngredient.objects.create(dish=dish, **ingredient_data)

        return dish
    
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
