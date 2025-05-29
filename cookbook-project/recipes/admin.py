"""
This file customizes the Django admin interface for the recipe app, enhancing how models are displayed and managed.
"""
import os
import gc
from django.core.exceptions import ValidationError
from django.contrib import admin
from django.utils.html import format_html
from .models import Dish, Ingredient, GroceryItem, CookingStep, DishIngredient, Unit
from .forms import DishForm, GroceryItemForm

class CookingStepInline(admin.TabularInline):
    model = CookingStep
    extra = 1                                                   # shows 1 empty form by default
    fields = ('step_number', 'instruction', 'image')
    ordering = ('step_number',)                                 # orders steps numerically

class DishIngredientInline(admin.TabularInline):
    model = DishIngredient
    extra = 1
    autocomplete_fields = ['ingredient', 'unit']

"""
This class customizes the Django admin interface for the Dish model.
methods
1. total_time
2. ingredient_list
3. image_preview
4. save_model
5. delete_queryset
6. save_formset
"""
@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    form = DishForm # Custom form for Dish                                                                      # custom form
    list_display = ('name', 'prep_time', 'cook_time', 'total_time', 'ingredient_list', 'image_preview')
    list_filter = ('prep_time', 'cook_time')
    search_fields = ('name',)
    inlines = [DishIngredientInline, CookingStepInline]
    
    # Edit view customization
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description','image', 'image_preview')
        }),
        ('Timing', {
            'fields': ('prep_time', 'cook_time')
        }),
    )
    readonly_fields = ('image_preview',)
    
    def total_time(self, obj):                                                    # calculates total time in mins of prep and cook time
        return f"{obj.prep_time + obj.cook_time} mins"
    total_time.short_description = 'Total Time'
    
    def ingredient_list(self, obj):                                               # lists first 3 ingredients of the dish               
        return ", ".join([i.name for i in obj.ingredients.all()[:3]])
    ingredient_list.short_description = 'Ingredients'

    def image_preview(self, obj):
        # show image if it exists
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px;" />', 
                obj.image.url
            )
        # placeholder if no image
        return format_html(
            '<img id="live-preview" style="max-height: 100px; display: none;"/>'
        )

    # this is a javascript file to show a live preview of the image
    class Media:
        js = ('admin/js/dish_preview.js',)

    """
    Override bulk deletion to properly delete images associated with dishes and steps
    """
    def delete_queryset(self, request, queryset):
        for dish in queryset:
            # delete main dish image
            try:
                if dish.image and os.path.isfile(dish.image.path):
                    os.remove(dish.image.path)
            except PermissionError:
                gc.collect()
                if dish.image and os.path.isfile(dish.image.path):
                    os.remove(dish.image.path)
            
            # delete all step images
            for step in dish.steps.all():
                try:
                    if step.image and os.path.isfile(step.image.path):
                        os.remove(step.image.path)
                except PermissionError:
                    gc.collect()
                    if step.image and os.path.isfile(step.image.path):
                        os.remove(step.image.path)

        super().delete_queryset(request, queryset)
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)                  # saves the formset but doesn't commit the changes to the DB yet
        for instance in instances:                              # iterate through each instance in the formset   
            if isinstance(instance, DishIngredient):            # if the instance is a DishIngredient
                if not instance.dish_id:                        # if the instance doesn't have a dish_id, set it
                    instance.dish = form.instance               # set the dish attribute to the instance of the Dish form being edited
            instance.save()                                     # saves each instance to the DB
        formset.save_m2m()                                      # saves the many-to-many relationships if any exist in the formset

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'dish_count')
    search_fields = ('name',)

    # djangos fetch option doesn't enforce ordering by default
    # this method's purpose is to make sure that the results are ordered alphabetically, this shows up in ingredients and adding grocery
    def get_search_results(self, request, queryset, search_term):
        # get the default results first
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Apply alphabetical ordering to autocomplete results
        queryset = queryset.order_by('name')
        return queryset, use_distinct
    
    def dish_count(self, obj):
        return obj.dish_set.count()
    dish_count.short_description = 'Used In # Dishes'

@admin.register(GroceryItem)
class GroceryItemAdmin(admin.ModelAdmin):
    form = GroceryItemForm
    list_display = ('name', 'in_cart', 'is_optional', 'created_at')
    list_editable = ('in_cart', 'is_optional')
    list_filter = ('in_cart', 'is_optional', 'created_at')
    search_fields = ('name',)
    ordering = ['-in_cart', 'name']
    
    # Remove the add view fields you don't want to show
    fields = ('name', 'in_cart', 'is_optional')
    
    def save_model(self, request, obj, form, change):
        # Check for duplicates in grocery items only (case-insensitive)
        duplicate_exists = GroceryItem.objects.filter(
            name__iexact=obj.name.strip()
        ).exclude(pk=obj.pk).exists()
        
        if duplicate_exists:
            raise ValidationError(
                f'"{obj.name}" already exists in your grocery list. '
                'Please edit the existing item instead.'
            )
        
        # Clean and save the name
        obj.name = obj.name.strip().title()  # Capitalize first letter of each word
        super().save_model(request, obj, form, change)
    
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation')
    search_fields = ('name', 'abbreviation')