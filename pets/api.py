"""JSON endpoints used by the dashboard JavaScript."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Pet
from .services import PetService


def serialize_pet(pet: Pet) -> dict:
    return {
        "name": pet.name,
        "hunger": pet.hunger,
        "happiness": pet.happiness,
        "energy": pet.energy,
        "level": getattr(pet, "level", 1),
        "xp": getattr(pet, "xp", 0),
        "xp_to_next": getattr(pet, "xp_to_next_level", 100),
        "coins": getattr(pet, "coins", 0),
        "stage": getattr(pet, "stage", "baby"),
        "is_alive": pet.is_alive,
        "overall": pet.overall_score,
    }


@login_required
@require_GET
def state(request):
    return JsonResponse(serialize_pet(request.user.pet))


@login_required
@require_POST
def feed(request):
    pet = PetService.feed(request.user.pet)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
def play(request):
    pet = PetService.play(request.user.pet)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
def sleep(request):
    pet = PetService.sleep(request.user.pet)
    return JsonResponse(serialize_pet(pet))
