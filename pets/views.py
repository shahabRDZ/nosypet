from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import PetService, SHOP_ITEMS


def home(request):
    if request.user.is_authenticated:
        return redirect("pets:dashboard")
    return render(request, "pets/home.html")


@login_required
def dashboard(request):
    pet = PetService.refresh(request.user.pet)
    return render(request, "pets/dashboard.html", {"pet": pet})


@login_required
def shop(request):
    pet = PetService.refresh(request.user.pet)
    items = [{"key": k, **v} for k, v in SHOP_ITEMS.items()]
    return render(request, "pets/shop.html", {"pet": pet, "items": items})
