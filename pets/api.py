"""JSON endpoints used by the dashboard JavaScript."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Pet
from .services import (
    InsufficientCoins,
    PetService,
    SHOP_ITEMS,
    UnknownItem,
)


def serialize_pet(pet: Pet) -> dict:
    return {
        "name": pet.name,
        "hunger": pet.hunger,
        "happiness": pet.happiness,
        "energy": pet.energy,
        "level": pet.level,
        "xp": pet.xp,
        "xp_to_next": pet.xp_to_next_level,
        "coins": pet.coins,
        "stage": pet.stage,
        "is_alive": pet.is_alive,
        "overall": pet.overall_score,
    }


@login_required
@require_GET
def state(request):
    pet = PetService.refresh(request.user.pet)
    return JsonResponse(serialize_pet(pet))


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


@login_required
@require_POST
def buy(request, item_key):
    try:
        pet = PetService.buy(request.user.pet, item_key)
    except UnknownItem:
        return JsonResponse({"error": "unknown_item"}, status=400)
    except InsufficientCoins:
        return JsonResponse({"error": "insufficient_coins"}, status=402)
    return JsonResponse(serialize_pet(pet))
