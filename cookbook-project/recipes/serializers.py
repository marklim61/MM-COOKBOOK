from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Dish, Ingredient, GroceryItem, CookingStep, Unit, DishIngredient

class BaseNormalizationMixin:
    """Shared normalization and validation logic"""
    def _normalize_name(self, name):
        return name.strip().lower()

    def _get_similar_terms(self, name):
        """Use the same similar terms logic as models"""
        name = name.strip().lower()
        similar_terms = [name]
        
        similar_groups = [
            ['pieces', 'piece', 'pcs', 'pc'],
            ['tablespoons', 'tablespoon', 'tbsp', 'tbs'],
            ['teaspoons', 'teaspoon', 'tsp', 'ts'],
            ['pounds', 'pound', 'lbs', 'lb'],
            ['ounces', 'ounce', 'oz'],
            ['cups', 'cup', 'c'],
            ['grams', 'gram', 'g'],
            ['kilograms', 'kilogram', 'kg'],
        ]

        for group in similar_groups:
            if name in group:
                similar_terms.extend(group)
                break
        
        return list(set(similar_terms))

    def _validate_model_instance(self, instance):
        """Helper to call model validation and convert Django ValidationError to DRF"""
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            if hasattr(e, 'error_dict'):
                raise serializers.ValidationError(e.error_dict)
            else:
                raise serializers.ValidationError(str(e))

class IngredientSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    def validate_name(self, value):
        # create temporary instance to test validation
        normalized_value = self._normalize_name(value)

        # check for similar terms conflicts manually since we can't rely on model validation here
        similar_terms = self._get_similar_terms(normalized_value)
        
        # build query to check for conflicts with similar terms
        query = models.Q()
        for term in similar_terms:
            query |= models.Q(name__iexact=term)
        
        # exclude current instance if updating
        existing_ingredients = Ingredient.objects.filter(query)
        if self.instance:
            existing_ingredients = existing_ingredients.exclude(pk=self.instance.pk)
        
        if existing_ingredients.exists():
            conflict = existing_ingredients.first()
            raise serializers.ValidationError(
                f'Similar ingredient already exists: "{conflict.name}" (ID: {conflict.id}). '
                f'Terms like "{", ".join(similar_terms)}" are considered duplicates.'
            )
        
        return normalized_value

    def create(self, validated_data):
        instance = Ingredient(**validated_data)
        self._validate_model_instance(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Ingredient
        fields = ["id", "name"]

class CookingStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = CookingStep
        fields = ["id", "step_number", "instruction", "image"]
        extra_kwargs = {"image": {"required": False}}

class UnitSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    def validate(self, data):
        if not data.get("name", "").strip():
            raise serializers.ValidationError({"name": "Name cannot be empty"})
        
        if "abbreviation" in data and not data["abbreviation"].strip():
            data["abbreviation"] = ""  # convert empty string to empty
        
        return data

    def _validate_unit_data(self, data, instance=None):
        """Validate using model logic"""
        temp_instance = Unit(
            name=self._normalize_name(data["name"]),
            abbreviation=self._normalize_name(data.get("abbreviation", "")) if data.get("abbreviation") else ""
        )
        
        if instance:
            temp_instance.pk = instance.pk
            
        self._validate_model_instance(temp_instance)
        return {
            "name": temp_instance.name,
            "abbreviation": temp_instance.abbreviation
        }

    def create(self, validated_data):
        validated_data = self._validate_unit_data(validated_data)
        instance = Unit(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        validated_data = self._validate_unit_data(validated_data, instance)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Unit
        fields = ["id", "name", "abbreviation"]

class DishIngredientSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), 
        required=False, 
        write_only=True,
        source='ingredient'
    )
    ingredient_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    ingredient_detail = IngredientSerializer(source="ingredient", read_only=True)

    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), 
        required=False, 
        write_only=True,
        source='unit'
    )
    unit_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    unit_detail = UnitSerializer(source="unit", read_only=True)

    class Meta:
        model = DishIngredient
        fields = [
            "id",
            "ingredient_id", 
            "ingredient_name",
            "ingredient_detail",
            "quantity",
            "unit_id",
            "unit_name",
            "unit_detail",
        ]

    def to_internal_value(self, data):
        """Handle both 'ingredient' and 'ingredient_id' field names for backward compatibility"""
        if isinstance(data, dict):
            data = data.copy()
            
            # handle ingredient
            if 'ingredient_id' in data:
                if isinstance(data['ingredient_id'], dict):
                    # if it's an object, extract the ID
                    data['ingredient_id'] = data['ingredient_id'].get('id', data['ingredient_id'])
            
            # handle unit
            if 'unit_id' in data:
                if isinstance(data['unit_id'], dict):
                    # if it's an object, extract the ID
                    data['unit_id'] = data['unit_id'].get('id', data['unit_id'])
        
        return super().to_internal_value(data)

    def _get_or_create_ingredient(self, name):
        """Get or create ingredient with proper validation"""
        normalized_name = self._normalize_name(name)
        
        # check for existing similar ingredients first
        similar_terms = self._get_similar_terms(normalized_name)
        query = models.Q()
        for term in similar_terms:
            query |= models.Q(name__iexact=term)
        
        existing = Ingredient.objects.filter(query).first()
        if existing:
            return existing
        
        # create new ingredient with validation
        ingredient = Ingredient(name=name.strip())
        self._validate_model_instance(ingredient)
        ingredient.save()
        return ingredient

    def _get_or_create_unit(self, name):
        """Get or create unit with proper validation"""
        normalized_name = self._normalize_name(name)
        
        # check for existing similar units
        similar_terms = self._get_similar_terms(normalized_name)
        query = models.Q()
        for term in similar_terms:
            query |= models.Q(name__iexact=term) | models.Q(abbreviation__iexact=term)
        
        existing = Unit.objects.filter(query).first()
        if existing:
            return existing
        
        # create new unit with validation
        unit = Unit(name=name.strip())
        self._validate_model_instance(unit)
        unit.save()
        return unit

    def create(self, validated_data):
        with transaction.atomic():
            # Handle ingredient - priority: ingredient_name over ingredient_id
            ingredient_from_name = None
            if 'ingredient_name' in validated_data:
                ingredient_name = validated_data.pop('ingredient_name')
                if ingredient_name and ingredient_name.strip():  # only if not empty
                    ingredient_from_name = self._get_or_create_ingredient(ingredient_name)
            
            # Handle unit - priority: unit_name over unit_id
            unit_from_name = None
            if 'unit_name' in validated_data:
                unit_name = validated_data.pop('unit_name')
                if unit_name and unit_name.strip():  # only if not empty
                    unit_from_name = self._get_or_create_unit(unit_name)
            
            # Set ingredient: prefer created from name, fallback to provided ID
            if ingredient_from_name:
                validated_data['ingredient'] = ingredient_from_name
            elif 'ingredient' not in validated_data or validated_data['ingredient'] is None:
                raise serializers.ValidationError("Either 'ingredient_id' or 'ingredient_name' must be provided")
            
            # Set unit: prefer created from name, fallback to provided ID
            if unit_from_name:
                validated_data['unit'] = unit_from_name
            
            return super().create(validated_data)

class DishSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    dishingredient_set = DishIngredientSerializer(many=True, required=False)
    steps = CookingStepSerializer(many=True, required=False)

    class Meta:
        model = Dish
        fields = [
            "id",
            "name",
            "description",
            "dishingredient_set",
            "steps",
            "prep_time",
            "cook_time",
            "image",
        ]
        extra_kwargs = {
            "image": {"required": False},
            "dish_ingredients": {"style": {"base_template": "textarea.html"}},
            "steps": {"style": {"base_template": "textarea.html"}},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["image"] = instance.image.url if instance.image else None
        return ret

    def create(self, validated_data):
        ingredients_data = validated_data.pop("dishingredient_set", [])
        steps_data = validated_data.pop("steps", [])

        dish = Dish.objects.create(**validated_data)

        ingredient_serializer = DishIngredientSerializer()

        # Create dish ingredients
        for ingredient_data in ingredients_data:
            data = ingredient_data.copy()
        
            # Handle ingredient
            if 'ingredient_name' in data:
                ingredient = ingredient_serializer._get_or_create_ingredient(data.pop('ingredient_name'))
                data['ingredient'] = ingredient
            
            # Handle unit
            if 'unit_name' in data:
                unit = ingredient_serializer._get_or_create_unit(data.pop('unit_name'))
                data['unit'] = unit
            
            DishIngredient.objects.create(dish=dish, **data)

        for step_data in steps_data:
            CookingStep.objects.create(dish=dish, **step_data)

        return dish
    
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("dishingredient_set", None)
        steps_data = validated_data.pop("steps", None)
        
        # Update the main dish fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle dish_ingredients if provided
        if ingredients_data is not None:
            with transaction.atomic():
                # Clear existing ingredients
                instance.dishingredient_set.all().delete()
                
                # Initialize the ingredient serializer to reuse its methods
                ingredient_serializer = DishIngredientSerializer()
                
                # Create new ingredients (handling both ID and name cases)
                for ingredient_data in ingredients_data:
                    data = ingredient_data.copy()
                    
                    # Handle ingredient
                    if 'ingredient_name' in data:
                        ingredient = ingredient_serializer._get_or_create_ingredient(data.pop('ingredient_name'))
                        data['ingredient'] = ingredient
                    
                    # Handle unit
                    if 'unit_name' in data:
                        unit = ingredient_serializer._get_or_create_unit(data.pop('unit_name'))
                        data['unit'] = unit
                    
                    DishIngredient.objects.create(dish=instance, **data)
        
        # Handle steps if provided
        if steps_data is not None:
            with transaction.atomic():
                # Clear existing steps
                instance.steps.all().delete()
                
                # Create new steps
                for step_data in steps_data:
                    CookingStep.objects.create(dish=instance, **step_data)
        
        return instance

class GrocerySerializer(serializers.ModelSerializer):
    class Meta:
        model = GroceryItem
        fields = [
            "id",
            "name",
            "in_cart",
            "is_optional",
            "created_at",
        ]
        read_only_fields = ['created_at']

    def validate_name(self, value):
        """Clean and validate the grocery item name"""
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Grocery item name cannot be empty.")
        
        # Check for case-insensitive duplicates (same logic as your admin)
        duplicate_exists = GroceryItem.objects.filter(
            name__iexact=name
        ).exclude(pk=self.instance.pk if self.instance else None).exists()
        
        if duplicate_exists:
            raise serializers.ValidationError(
                f'"{name}" already exists in your grocery list. '
                'Please edit the existing item instead.'
            )
        
        return name.title()  # Capitalize first letter of each word

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)