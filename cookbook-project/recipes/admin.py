"""
This file customizes the Django admin interface for the recipe app, enhancing how models are displayed and managed.
"""
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import Dish, Ingredient, Grocery, CookingStep, DishIngredient, Unit
from .forms import DishForm
import os

class CookingStepInline(admin.TabularInline):
    model = CookingStep
    extra = 1
    fields = ('step_number', 'instruction', 'image')
    ordering = ('step_number',)

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
    form = DishForm
    list_display = ('name', 'prep_time', 'cook_time', 'total_time', 'ingredient_list', 'image_preview')
    list_filter = ('prep_time', 'cook_time')
    search_fields = ('name',)
    filter_horizontal = ()
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
    
    def total_time(self, obj):                        
        return f"{obj.prep_time + obj.cook_time} mins"
    total_time.short_description = 'Total Time'
    
    def ingredient_list(self, obj):
        return ", ".join([i.name for i in obj.ingredients.all()[:3]])
    ingredient_list.short_description = 'Ingredients'

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px;" />', 
                obj.image.url
            )
        # For new unsaved objects
        return format_html(
            '<img id="live-preview" style="max-height: 100px; display: none;"/>'
        )

    class Media:
        js = ('admin/js/dish_preview.js',)

    # Just in case the dish gets saved without ingredients, delete it
    # Note, there will be two errors, because I think Django's defaukt save method is called causing the success message, but it deletes the dish properly
    # def save_model(self, request, obj, form, change):
    #     if not form.cleaned_data.get('ingredients'):
    #         messages.error(
    #             request,
    #             f"Cannot save '{obj.name}' without ingredients!",
    #             extra_tags="danger"
    #         )
    #         return
    #     super().save_model(request, obj, form, change)

    """
    Override bulk deletion to properly delete images
    """
    def delete_queryset(self, request, queryset):
        for dish in queryset:
            # Delete main dish image
            if dish.image:
                try:
                    if os.path.isfile(dish.image.path):
                        os.remove(dish.image.path)
                except PermissionError:
                    import gc
                    gc.collect()
                    if os.path.isfile(dish.image.path):
                        os.remove(dish.image.path)
            
            # Delete all step images
            for step in dish.steps.all():
                if step.image:
                    try:
                        if os.path.isfile(step.image.path):
                            os.remove(step.image.path)
                    except PermissionError:
                        import gc
                        gc.collect()
                        if os.path.isfile(step.image.path):
                            os.remove(step.image.path)
        
        # Now perform the bulk deletion
        super().delete_queryset(request, queryset)
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            # If it's a DishIngredient, make sure dish is set
            if isinstance(instance, DishIngredient):
                if not instance.dish_id:
                    instance.dish = form.instance
            instance.save()
        formset.save_m2m()

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'dish_count')
    search_fields = ('name',)

    def save_model(self, request, obj, form, change):
        # convert name to lowercase before saving
        obj.name = obj.name.lower()
        super().save_model(request, obj, form, change)
    
    def dish_count(self, obj):
        return obj.dish_set.count()
    dish_count.short_description = 'Used In # Dishes'

@admin.register(Grocery)
class GroceryAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'purchased', 'created_at')
    list_editable = ('purchased',)
    autocomplete_fields = ['ingredient']  # Now this will work
    
    # Optional: customize how ingredients appear in the autocomplete
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['ingredient'].label_from_instance = lambda inst: inst.name
        return form
    
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation')
    search_fields = ('name', 'abbreviation')

    def save_model(self, request, obj, form, change):
        # convert name and abbreviation to lowercase before saving
        obj.name = obj.name.lower()
        obj.abbreviation = obj.abbreviation.lower()
        super().save_model(request, obj, form, change)