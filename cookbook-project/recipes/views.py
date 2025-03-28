from django.shortcuts import render
from .models import Dish

# Create your views here.
def dish_list(request):                                                 # Defines a function dish_list, all Django view functions take a request parameter(contains info about the user's web request)
    dishes = Dish.objects.all()                                         # Get all dishes from DB
    return render(request, 'recipes/list.html', {'dishes': dishes})     # The HTTP request object, the name of the template to render, and a dictionary of variables to pass to the template