"""
Models for the recipe app.
This file defines the structure of the database tables for the app.
It serves as the single source of truth for how the data is stored, retrieved, and validated.
"""
from django.db import models
from django.core.validators import (   
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
)
from django.core.exceptions import ValidationError
import os

"""
Ingredient model to store information about each ingredients with a single field for name.
And only two methods: 
1. __str__
2. dish_count.
"""
class Ingredient(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        error_messages={
            "unique": "This ingredient name already exist."
        },
    )

    def __str__(self):                                          # Returns a string of the ingredient, which is the name of the ingredient
        return (
            self.name
        )

    def dish_count(self):                                       # Returns the number of dishes that use this ingredient
        return self.dish_set.count()

    dish_count.short_description = "Used In # Dishes"           # Renames the column in the admin panel


"""
Dish model to store information about each dish with fields for name, description, ingredients, prep_time, cook_time, and image.
And only two methods: 
1. __str__
2. total_time.
"""
class Dish(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        error_messages={"unique": "This dish name already exist."},
    )
    description = models.TextField(blank=True)
    ingredients = models.ManyToManyField(
        Ingredient,
        through="DishIngredient",                               # DishIngredient is the intermediate model that connects Dish and Ingredient
        through_fields=("dish", "ingredient"),                  # This allows Django to create m2m relationships between Dish and Ingredient through DishIngredient
    )                                                           # Example: Dish: Pasta, Ingredient: Ground Beef, DishIngredient: Pasta -> 2 lbs Ground Beef
    prep_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                1, message="Prep time must be at least 1 minute."
            ),
            MaxValueValidator(
                1440, message="Prep time cannot exceed 24 hours."
            ),
        ]
    )
    cook_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                0, message="Cook time cannot be negative."
            ),
            MaxValueValidator(
                1440, message="Cook time cannot exceed 24 hours."
            ),
        ]
    )
    """
    This was added to because I wanted users to upload images of their dishes from their phones
    also to prevent too large images being uploaded
    """
    def validate_image_size(value):
        filesize = value.size
        max_size = 5 * 1024 * 1024                      # 5MB, iPhone photos are often 3-8MB
        if filesize > max_size:
            raise ValidationError(
                f"Max image size is {max_size/1024/1024}MB. Your file is {filesize/1024/1024:.1f}MB."
            )

    """
    Same as above, but for the image dimensions
    3000x3000px is a good size for most phones and tablets
    also I want the iamges to be uniform in size for the grid view
    """
    def validate_image_dimensions(value):
        from PIL import Image                           # Import the Image class

        img = Image.open(value)                         # Open the image
        width, height = img.size                        # Get the image dimensions
        max_resolution = 3000                           # 3K resolution
        if (
            width > max_resolution or height > max_resolution
        ):
            raise ValidationError(
                f"Max resolution is {max_resolution}x{max_resolution}px. Your image is {width}x{height}px."
            )

    image = models.ImageField(
        upload_to="dish_images/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp"]
            ),
            validate_image_size,
            validate_image_dimensions,
        ],
        help_text="Upload image (max 5MB, 3000x3000px, JPG/PNG/WEBP)",
    )

    """
    Checks the following:
    1. Prep time and cook time are not None
    2. Total time does not exceed 4 hours
    """
    def clean(self):
        """
        Creating an empty dictionary to store errors allows the method to collect
        and store multiple errors in a single data structure, so it can return a single error
        object all the error messages, rather than raising an error for each validation failure.
        """
        errors = {}                                

        if self.prep_time is None:
            errors["prep_time"] = "Prep time is required."
        if self.cook_time is None:
            errors["cook_time"] = "Cook time is required."

        """
        Only check total time if both times exist
        We don't want to check if one of them is None
        """
        if self.prep_time is not None and self.cook_time is not None:
            if (self.prep_time + self.cook_time) > 240:
                errors["cook_time"] = "Total cooking time exceeds 4 hours."

        if errors:
            raise ValidationError(errors)

    def total_time(self):
        return (
            self.prep_time + self.cook_time
        )

    def __str__(self): 
        return self.name

    """
    Delete all associated images when dish is deleted from the database.
    This is to prevent orphaned images from being left on the server.
    Note: gc is a garbage collector, it helps manage memory by automatically deleting objects that are no longer needed.
    Note: PermissionError is an exception class in Python that is raised when a program attempts to perform an operation that requires permission or access rights.
    """
    def delete(self, *args, **kwargs):
        if self.image:
            try:
                if os.path.isfile(self.image.path):
                    os.remove(self.image.path)
            except PermissionError:
                import gc

                gc.collect()
                if os.path.isfile(self.image.path):
                    os.remove(self.image.path)

        # Delete all step images
        for step in self.steps.all():  # Uses the reverse relation from Dish to CookingStep, allows access to all steps for this dish
            if step.image:
                try:
                    if os.path.isfile(step.image.path):
                        os.remove(step.image.path)
                except PermissionError:
                    import gc

                    gc.collect()
                    if os.path.isfile(step.image.path):
                        os.remove(step.image.path)

        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Delete old image if being updated with a new one"""
        if self.pk:  # Only for existing instances
            try:
                old_instance = Dish.objects.get(pk=self.pk)
                if old_instance.image and old_instance.image != self.image:
                    if os.path.isfile(old_instance.image.path):
                        os.remove(old_instance.image.path)
            except Dish.DoesNotExist:
                pass
        super().save(*args, **kwargs)

"""
This model is used to store the units of measurement for ingredients.
"""
class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True)
    abbreviation = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.abbreviation if self.abbreviation else self.name

"""
This model is used to store the ingredients for each dish.
"""
class DishIngredient(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)

    class Meta:
        unique_together = (
            "dish",
            "ingredient",
        )  # Each ingredient can only appear once per dish

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient} for {self.dish}"

"""
This model is used to store the groceries for each ingredient.
"""
class Grocery(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Item to buy"
    )
    purchased = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.ingredient)

    class Meta:
        verbose_name_plural = "Groceries"
        ordering = ["-purchased", "ingredient__name"]

"""
This model is used to store the steps for each dish.
Two methods:
1. delete 
2. save
"""
class CookingStep(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name="steps")
    step_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    instruction = models.TextField()
    image = models.ImageField(
        upload_to="step_images/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
        ],
    )

    class Meta:
        ordering = ["step_number"]
        unique_together = [
            "dish",
            "step_number",
        ]  # Prevent duplicate step numbers for the same dish

    def __str__(self):
        return f"Step {self.step_number} for {self.dish.name}"

    def delete(self, *args, **kwargs):
        """Delete the image file when the step is deleted"""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Delete old image if being updated with a new one"""
        if self.pk:  # Only for existing instances
            try:
                old_instance = CookingStep.objects.get(pk=self.pk)
                if old_instance.image and old_instance.image != self.image:
                    if os.path.isfile(old_instance.image.path):
                        os.remove(old_instance.image.path)
            except CookingStep.DoesNotExist:
                pass
        super().save(*args, **kwargs)