from django import forms                                            # Import the forms module        
from .models import Dish                                            # Import the Dish model

class DishForm(forms.ModelForm):                                    # Create a form based on the Dish model
    class Meta:                                                     # Define the form fields
        model = Dish                                                # Use the Dish model
        fields = '__all__'                                          # Include all fields
    
    def __init__(self, *args, **kwargs):                            # Initialize the form
        super().__init__(*args, **kwargs)                           # Call the parent constructor
        self.fields['ingredients'].required = True                  # Make the ingredients field required
        self.fields['ingredients'].help_text = 'Select at least one ingredient'
        
        # Add HTML5 attributes
        self.fields['prep_time'].widget.attrs['min'] = 1            # Set the minimum value to 1
        self.fields['prep_time'].widget.attrs['max'] = 1440         # Set the maximum value to 1440
        self.fields['cook_time'].widget.attrs['min'] = 0            # Set the minimum value to 0
        self.fields['cook_time'].widget.attrs['max'] = 1440         # Set the maximum value to 1440
        
    def clean(self):
        cleaned_data = super().clean()                              
        # Check ingredients from form data (works before save)
        if not cleaned_data.get('ingredients'):                     # If no ingredients were provided
            self.add_error('ingredients', "Please select at least one ingredient.")
        return cleaned_data                                         # Return the cleaned data
        # return self.data                                            # To intentionally skip validation to test the error in the admin if the dish gets saved without ingredients