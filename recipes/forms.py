"""
This file defines Django forms that handle user input for creating and updating model instances (Dish, Grocery)
"""
from django import forms     
from .models import Dish, GroceryItem, Ingredient
from django.urls import reverse_lazy

"""
This form is used to create or update Dish objects.
"""
class DishForm(forms.ModelForm):
    class Meta:
        model = Dish
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'ingredients' in self.fields:
            del self.fields['ingredients']                              # remove the 'ingredients' field since i'm using DishIngredientInline

        self.fields['prep_time'].widget.attrs['min'] = 1
        self.fields['prep_time'].widget.attrs['max'] = 1440
        self.fields['cook_time'].widget.attrs['min'] = 0
        self.fields['cook_time'].widget.attrs['max'] = 1440

    # commented out because I learned that djangle handles clean() method automatically, removed save() method too for the same reason    
    # def clean(self):
    #     cleaned_data = super().clean()                              
    #     return cleaned_data                                         # return the cleaned data
        # return self.data                                            # this is used to intentionally skip validation to test the error in the admin if the dish gets saved without ingredients
    
"""
This form is used to create or update Grocery objects.
"""
class GroceryItemForm(forms.ModelForm):
    class Meta:
        model = GroceryItem
        fields = ['name', 'in_cart', 'is_optional']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter grocery item name...',
                'class': 'grocery-item-input',
                'style': 'width: 300px;'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = "Enter the name of the grocery item"
        
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Grocery item name cannot be empty.")
        return name.title()  # Capitalize first letter of each word