from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control

from .models import Pet
from .services import PetService


def home(request):
    if request.user.is_authenticated:
        return redirect("pets:dashboard")
    return render(request, "pets/home.html")


@login_required
def dashboard(request):
    try:
        pet = request.user.pet
    except Pet.DoesNotExist:
        # Superusers created before the auto-create signal existed end
        # up here. Make one on demand so the dashboard always works.
        pet = Pet.objects.create(owner=request.user)
    pet = PetService.refresh(pet)
    return render(request, "pets/dashboard.html", {"pet": pet})


# PWA: manifest and service worker must live at the site root so the
# service worker's scope covers the whole site. Rendering them through
# Django (rather than dropping them in /static) gives us correct content
# types and lets us reverse the static URL for the icon.
@cache_control(public=True, max_age=3600)
def manifest(request):
    return render(request, "pets/manifest.webmanifest", content_type="application/manifest+json")


@cache_control(public=True, max_age=3600)
def service_worker(request):
    body = render(request, "pets/sw.js").content
    response = HttpResponse(body, content_type="application/javascript")
    # Allow the SW to control the entire origin.
    response["Service-Worker-Allowed"] = "/"
    return response
