from django.db import models                                                            # Import the models module
from django.core.validators import MinValueValidator, MaxValueValidator                 # Import the MinValueValidator and MaxValueValidator classes
from django.core.exceptions import ValidationError                                      # Import the ValidationError class

# Ingredient model to store information about each ingredients
class Ingredient(models.Model):
    UNIT_CHOICES = [                                                                    # Unit choices
        ('g', 'grams'),
        ('ml', 'milliliters'),
        ('tsp', 'teaspoons'),
        ('tbsp', 'tablespoons'),
        ('cup', 'cups'),
        ('pcs', 'pieces'),
    ]

    name = models.CharField(                                                            # Ingredient name
        max_length=100,                                                                 # up to 100 characters
        unique=True,                                                                    # unique=True to prevent duplicates
        error_messages={'unique': 'This ingredient name already exist.'}                # custom error message
    )
    quantity = models.FloatField(
        validators =[MinValueValidator(0.01, message="Quantity must be at least 0.01")] # Quantity must be at least 0.01
    )
    unit = models.CharField(
        max_length=10,                                                                  # up to 10 characters
        choices=UNIT_CHOICES,                                                           # choices=UNIT_CHOICES
        blank=True                                                                      # Optional field
    )

    def clean(self):                                                                    # Validate the ingredient
        if self.unit == 'pcs' and not self.quantity.is_integer():                       # If the unit is 'pcs' and the quantity is not an integer
            raise ValidationError({'quantity': 'Piece counts must be whole numbers.'})  # Raise a validation error
        
    def __str__(self):                                                                  # _str_ controls how the object is displayed
        return f"{self.name} - {self.quantity} {self.unit}"                             # for example: "Sugar - 2.5 cups"

# Dish model to store dishes and their recipes
class Dish(models.Model):
    name = models.CharField(                                                        # Dish name
        max_length=100,                                                             # up to 100 characters
        unique=True,                                                                # unique=True to prevent duplicates
        error_messages={'unique': 'This dish name already exist.'})                 # custom error message
    description = models.TextField(blank=True)                                      # Optional dish description
    ingredients = models.ManyToManyField(Ingredient)                                # Many-to-many relationship with Ingredient
    prep_time = models.PositiveIntegerField(
        validators=[                                                                # Validate the prep time
            MinValueValidator(1, message="Prep time must be at least 1 minute."),   # Minimum value is 1 minute
            MaxValueValidator(1440, message="Prep time cannot exceed 24 hours.")    # Maximum value is 24 hours
        ]
    )
    cook_time = models.PositiveIntegerField(
        validators=[                                                                # Validate the cook time
            MinValueValidator(0, message="Cook time cannot be negative."),          # Minimum value is 0
            MaxValueValidator(1440, message="Cook time cannot exceed 24 hours.")    # Maximum value is 24 hours
        ]
    )
    
    image = models.ImageField(
        upload_to='dish_images/',                                                   # Specify the directory to store the image
        blank=True,                                                                 # Optional field
        validators=[                                                                # Validate the image
            # Add file size/type validator if needed
        ]
    )

    def clean(self):                                                                    # Validate the dish
        errors = {}                                                                     # Create an empty dictionary to store errors
        
        if self.prep_time is None:
            errors['prep_time'] = "Prep time is required."                              # Add an error message
        if self.cook_time is None:
            errors['cook_time'] = "Cook time is required."                              # Add an error message

        # Only check total time if both times exist
        if self.prep_time is not None and self.cook_time is not None:
            if (self.prep_time + self.cook_time) > 240:
                errors['cook_time'] = "Total cooking time exceeds 4 hours."
        
        # Validate image dimensions (example)
        if self.image:                                                                  # If the image field is not empty
            if self.image.width > 2000 or self.image.height > 2000:                     # If the image width or height exceeds 2000 pixels
                errors['image'] = "Image dimensions cannot exceed 2000x2000 pixels."    # Add an error message
        
        if errors:                                                                      # If there are any errors
            raise ValidationError(errors)                                               # Raise a validation error

    def total_time(self):                                                               # Calculate the total time
        return self.prep_time + self.cook_time                                          # Return the sum of prep_time and cook_time

    def __str__(self):                                                                  # _str_ controls how the object is displayed
        return self.name                                                                # for example: "Pancakes"