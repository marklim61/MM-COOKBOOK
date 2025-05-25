from django.db import models
from django.db import transaction
from rest_framework import serializers
from .models import Dish, Ingredient, Grocery, CookingStep, Unit, DishIngredient
import inflect

p = inflect.engine()

class BaseNormalizationMixin:
    """Shared normalization and validation logic"""
    def _normalize_name(self, name, is_ingredient=False, is_unit=False):
        name = name.strip().lower()
        if is_ingredient:
            return p.singular_noun(name) or name
        if is_unit:
            return name[:-1] if name.endswith("s") and len(name) > 1 else name
        return name

    def _validate_unique_name(self, model, name_field, value, exclude_id=None):
        norm_name = self._normalize_name(value, is_ingredient=(model == Ingredient))
        query = model.objects.filter(
            models.Q(**{f"{name_field}__iexact": norm_name})
            | models.Q(**{f"{name_field}__iexact": p.plural(norm_name)})
        )

        if exclude_id:
            query = query.exclude(id=exclude_id)

        if conflict := query.first():
            raise serializers.ValidationError(
                f'Use existing "{getattr(conflict, name_field)}" (ID: {conflict.id}) instead'
            )
        return norm_name

class IngredientSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    def validate_name(self, value):
        return self._validate_unique_name(Ingredient, "name", value)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["name"] = self._validate_unique_name(
                Ingredient, "name", validated_data["name"], instance.id
            )
        return super().update(instance, validated_data)

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
        for field in ["name", "abbreviation"]:
            if not data.get(field, "").strip():
                raise serializers.ValidationError(
                    {field: f"{field.capitalize()} cannot be empty"}
                )
        return data

    def _validate_unit(self, data, instance=None):
        data["name"] = self._normalize_name(data["name"], is_unit=True)
        data["abbreviation"] = self._normalize_name(data["abbreviation"], is_unit=True)

        query = Unit.objects.filter(
            models.Q(name__iexact=data["name"])
            | models.Q(abbreviation__iexact=data["abbreviation"])
        )

        if instance:
            query = query.exclude(id=instance.id)

        if conflict := query.first():
            raise serializers.ValidationError(
                {"name": f'Unit conflict with "{conflict.name}" (ID: {conflict.id})'}
            )
        return data

    def create(self, validated_data):
        validated_data = self._validate_unit(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._validate_unit(validated_data, instance)
        return super().update(instance, validated_data)

    class Meta:
        model = Unit
        fields = ["id", "name", "abbreviation"]

class DishIngredientSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    ingredient = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), required=False, pk_field=serializers.IntegerField()
    )
    ingredient_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    ingredient_detail = IngredientSerializer(source="ingredient", read_only=True)

    unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), required=False, pk_field=serializers.IntegerField()
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

    def validate(self, data):
        if "ingredient_name" in data:
            data["ingredient_name"] = self._validate_unique_name(
                Ingredient, "name", data["ingredient_name"]
            )

        if "unit_name" in data:
            norm_unit = self._normalize_name(data["unit_name"], is_unit=True)
            conflict = Unit.objects.filter(
                models.Q(name__iexact=norm_unit)
                | models.Q(abbreviation__iexact=norm_unit[:3])
            ).first()

            if conflict:
                raise serializers.ValidationError(
                    {
                        "unit_name": f'Unit conflict with "{conflict.name}" (ID: {conflict.id})'
                    }
                )
            data["unit_name"] = norm_unit

        return data

    def _handle_ingredient_or_unit(self, field_name, model, validated_data):
        if f"{field_name}_name" in validated_data:
            name = validated_data.pop(f"{field_name}_name")
            is_ingredient = model == Ingredient
            norm_name = self._normalize_name(
                name, is_ingredient=is_ingredient, is_unit=not is_ingredient
            )

            obj, _ = model.objects.get_or_create(
                name__iexact=norm_name, defaults={"name": norm_name}
            )
            validated_data[field_name] = obj

    def create(self, validated_data):
        with transaction.atomic():
            self._handle_ingredient_or_unit("ingredient", Ingredient, validated_data)
            self._handle_ingredient_or_unit("unit", Unit, validated_data)
            return super().create(validated_data)

class DishSerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    dish_ingredients = DishIngredientSerializer(
        source="dishingredient_set", many=True, required=False
    )
    steps = CookingStepSerializer(many=True, required=False)

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

        for ingredient_data in ingredients_data:
        # Handle ingredient
            ingredient = None
            if 'ingredient' in ingredient_data:
                # Case 1: Using existing ingredient by ID
                ingredient = ingredient_data['ingredient']
            elif 'ingredient_name' in ingredient_data:
                # Case 2: Creating new ingredient by name
                norm_name = self._normalize_name(ingredient_data['ingredient_name'], is_ingredient=True)
                ingredient, _ = Ingredient.objects.get_or_create(
                    name__iexact=norm_name, 
                    defaults={'name': norm_name}
                )
            else:
                raise serializers.ValidationError("Either 'ingredient' or 'ingredient_name' must be provided")
            
            # Handle unit
            unit = None
            if 'unit' in ingredient_data:
                # Case 1: Using existing unit by ID
                unit = ingredient_data['unit']
            elif 'unit_name' in ingredient_data:
                # Case 2: Creating new unit by name
                norm_unit = self._normalize_name(ingredient_data['unit_name'], is_unit=True)
                unit, _ = Unit.objects.get_or_create(
                    name__iexact=norm_unit,
                    defaults={'name': norm_unit}
                )
            else:
                raise serializers.ValidationError("Either 'unit' or 'unit_name' must be provided")

            # Validate quantity
            if 'quantity' not in ingredient_data:
                raise serializers.ValidationError("Quantity is required")

            # Create DishIngredient
            DishIngredient.objects.create(
                dish=dish,
                ingredient=ingredient,
                unit=unit,
                quantity=ingredient_data['quantity']
            )

        for step_data in steps_data:
            CookingStep.objects.create(dish=dish, **step_data)

        return dish

class GrocerySerializer(serializers.ModelSerializer, BaseNormalizationMixin):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    new_ingredient = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

    class Meta:
        model = Grocery
        fields = [
            "id",
            "ingredient",
            "ingredient_name",
            "purchased",
            "created_at",
            "new_ingredient",
        ]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields.pop("new_ingredient", None)
        return fields

    def validate(self, data):
        if self.instance is None:
            new_ingredient = data.get("new_ingredient", "").strip()
            existing_ingredient = data.get("ingredient")

            if new_ingredient:
                norm_name = self._normalize_name(new_ingredient, is_ingredient=True)
                if Grocery.objects.filter(
                    ingredient__name__iexact=norm_name, purchased=False
                ).exists():
                    raise serializers.ValidationError(
                        "This ingredient is already in your grocery list"
                    )
            elif not existing_ingredient:
                raise serializers.ValidationError(
                    "You must provide either an existing ingredient or a new one"
                )
        return data

    def create(self, validated_data):
        new_ingredient = validated_data.pop("new_ingredient", "").strip()

        if new_ingredient:
            norm_name = self._normalize_name(new_ingredient, is_ingredient=True)
            ingredient, _ = Ingredient.objects.get_or_create(
                name__iexact=norm_name, defaults={"name": norm_name}
            )
            validated_data["ingredient"] = ingredient

        return super().create(validated_data)