from django.contrib import admin                        # Import the admin module
from .models import Dish, Ingredient                    # Import the Dish and Ingredient models to the admin panel
from django.utils.html import format_html               # This is for image previews
from .forms import DishForm                             # Import the DishForm
from django.contrib import messages                     # Import the messages module

# Register your models here.
@admin.register(Dish)                                                                                   # More modern registration decorator
class DishAdmin(admin.ModelAdmin):
    form = DishForm                                                                                     # Use our custom form
    list_display = ('name', 'prep_time', 'cook_time', 'total_time', 'ingredient_list', 'image_preview') # Display these fields
    list_filter = ('prep_time', 'cook_time')                                                            # Adds filters sidebar
    search_fields = ('name',)                                                                           # Adds search box
    filter_horizontal = ('ingredients',)                                                                # Better many-to-many widget
    
    # Edit view customization
    fieldsets = (                                                                                       # Group fields
        ('Basic Info', {
            'fields': ('name', 'image', 'image_preview')
        }),
        ('Timing', {
            'fields': ('prep_time', 'cook_time')
        }),
        ('Ingredients', {
            'fields': ('ingredients',)
        }),
    )
    readonly_fields = ('image_preview',)                                                                # Make preview read-only
    
    # Custom methods for list view
    def total_time(self, obj):                                                                          # Calculate the total time                             
        return f"{obj.prep_time + obj.cook_time} mins"                                                  # Return the total time
    total_time.short_description = 'Total Time'                                                         # Rename the column     
    
    def ingredient_list(self, obj):                                                                     # Show first 3 ingredients     
        return ", ".join([i.name for i in obj.ingredients.all()[:3]])                                   # Show first 3 ingredients
    ingredient_list.short_description = 'Ingredients'                                                   # Rename the column      
    
    def image_preview(self, obj):                                                                       # Show the image        
        if obj.image:                                                                                   # If the image field is not empty
            return format_html('<img src="{}" width="100" />', obj.image.url)                           # Show the image
        return "No image"                                                                               # If the image field is empty
    image_preview.short_description = 'Preview'                                                         # Rename the column

    # Just in case the dish gets saved without ingredients, delete it
    # Note, there will be two errors, because I think Django's defaukt save method is called causing the success message, but it deletes the dish properly
    def save_model(self, request, obj, form, change):                                                   # Save the model
        if not form.cleaned_data.get('ingredients'):                                                    # If the ingredients field is empty
            messages.error(                                                                             # Show an error message
                request,
                f"Cannot save '{obj.name}' without ingredients!",
                extra_tags="danger"
            )
            return                                                                                      # Exit without saving
    
        super().save_model(request, obj, form, change)                                                  # Only save if ingredients exist

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit', 'quantity_with_unit', 'dish_count')                     # Display these fields
    list_editable = ('quantity', 'unit')                                                                # Edit directly from list
    search_fields = ('name',)                                                                           # Search by ingredient name
    list_filter = ('unit',)                                                                             # Filter by unit    

    def quantity_with_unit(self, obj):
        return f"{obj.quantity} {obj.unit}" if obj.unit else obj.quantity
    quantity_with_unit.short_description = 'Amount'
    
    def dish_count(self, obj):
        return obj.dish_set.count()
    dish_count.short_description = 'Used In # Dishes'

    def save_model(self, request, obj, form, change):                                                   # Save the model
        if obj.quantity <= 0:                                                                           # If the quantity is less than or equal to 0
            messages.error(request, "Quantity must be positive.", extra_tags="danger")                  # Show an error message
            return                                                                                      # Don't save the model
        super().save_model(request, obj, form, change)                                                  # Call the parent method