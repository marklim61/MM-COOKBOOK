"""
This file defines Django forms that handle user input for creating and updating model instances (Dish, Grocery)
"""
from django import forms     
from .models import Dish, Grocery, Ingredient
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
class GroceryForm(forms.ModelForm):
    new_ingredient = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Add new ingredient...',
            'class': 'new-ingredient-input',
            'style': 'display: none;'
        })
    )

    class Meta:
        model = Grocery
        fields = ['ingredient']
        widgets = {
            'ingredient': forms.Select(attrs={
                'class': 'ingredient-select',
                'data-add-url': reverse_lazy('admin:recipes_ingredient_add')
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingredient'].queryset = Ingredient.objects.order_by('name')          # it sets the list of ingredients to be displayed in the form's dropdown menu
        # self.fields['ingredient'].required = False                                              # it makes the 'ingredient' field optional, allowing the field to be submitted empty                    

    """
    This method is used to validate the form data.
    If the ingredient field is not specified and the new_ingredient field is empty, it raises a ValidationError.
    therwise, it calls the parent class's clean method to validate the data.
    """
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('ingredient') and not cleaned_data.get('new_ingredient'):
            raise forms.ValidationError("You must select an ingredient or add a new one.")
        return cleaned_data

    """
    If the form contains a new ingredient, it creates a new Ingredient object and
    assigns it to the Grocery object before saving it.

    Args:
        commit (bool): Whether to commit the changes to the database. Defaults to True.

    Returns:
        Grocery: The saved Grocery object.
    """
    def save(self, commit=True):
        if self.cleaned_data.get('new_ingredient'):
            new_ingredient, _ = Ingredient.objects.get_or_create(
                name=self.cleaned_data['new_ingredient']
            )
            self.instance.ingredient = new_ingredient
        return super().save(commit)