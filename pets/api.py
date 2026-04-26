"""JSON endpoints used by the dashboard JavaScript.

Each mutating endpoint is rate limited per-user. The state endpoint is
left unrestricted because it is polled every few seconds.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from .models import HEAL_COST, Pet
from .services import (
    InsufficientCoins,
    InvalidName,
    PetService,
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
        "heal_cost": HEAL_COST,
    }


def _get_pet_or_404(user):
    """Return the user's pet or None if missing (e.g. for superusers
    created before the auto-create signal was registered)."""
    try:
        return user.pet
    except Pet.DoesNotExist:
        return None


@login_required
@require_GET
def state(request):
    pet = _get_pet_or_404(request.user)
    if pet is None:
        return JsonResponse({"error": "no_pet"}, status=404)
    pet = PetService.refresh(pet)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
@ratelimit(key="user", rate="30/m", method="POST", block=True)
def feed(request):
    pet = PetService.feed(request.user)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
@ratelimit(key="user", rate="30/m", method="POST", block=True)
def play(request):
    pet = PetService.play(request.user)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
@ratelimit(key="user", rate="30/m", method="POST", block=True)
def sleep(request):
    pet = PetService.sleep(request.user)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def heal(request):
    try:
        pet = PetService.heal(request.user)
    except InsufficientCoins:
        return JsonResponse({"error": "insufficient_coins"}, status=402)
    return JsonResponse(serialize_pet(pet))


@login_required
@require_POST
@ratelimit(key="user", rate="6/m", method="POST", block=True)
def rename(request):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "bad_json"}, status=400)
    try:
        pet = PetService.rename(request.user, payload.get("name", ""))
    except InvalidName:
        return JsonResponse({"error": "invalid_name"}, status=400)
    return JsonResponse(serialize_pet(pet))
