from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("pets:dashboard")
    return render(request, "pets/home.html")


@login_required
def dashboard(request):
    pet = request.user.pet
    return render(request, "pets/dashboard.html", {"pet": pet})
