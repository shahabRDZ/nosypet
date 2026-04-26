"""Business logic for pet actions.

Each mutation runs in a database transaction with `select_for_update`
on the pet row, so two concurrent requests from the same user cannot
race each other into a lost update. Every action also writes a
PetActionLog row for analytics and for the recent-activity feed.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import HEAL_COST, Pet, PetActionLog

User = get_user_model()

XP_PER_ACTION = {"feed": 8, "play": 12, "sleep": 6}
COINS_PER_ACTION = {"feed": 1, "play": 3, "sleep": 1}
NAME_MAX_LEN = 30


class InsufficientCoins(Exception):
    pass


class InvalidName(Exception):
    pass


def _clamp(value: int) -> int:
    return max(0, min(Pet.STAT_MAX, value))


def _locked_pet(user) -> Pet:
    """Fetch the user's pet with a row-level lock for the rest of the txn."""
    return Pet.objects.select_for_update().get(owner=user)


def _log(pet: Pet, action: str, detail: str = "") -> None:
    PetActionLog.objects.create(pet=pet, action=action, detail=detail)


class PetService:
    @staticmethod
    def refresh(pet: Pet) -> Pet:
        """Read-side decay update. No lock needed; saves only when changed."""
        pet.apply_decay(save=True)
        return pet

    @staticmethod
    @transaction.atomic
    def feed(user) -> Pet:
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        pet.hunger = _clamp(pet.hunger + 25)
        pet.energy = _clamp(pet.energy + 5)
        pet.add_xp(XP_PER_ACTION["feed"])
        pet.coins += COINS_PER_ACTION["feed"]
        pet.save()
        _log(pet, PetActionLog.ACTION_FEED)
        return pet

    @staticmethod
    @transaction.atomic
    def play(user) -> Pet:
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        pet.happiness = _clamp(pet.happiness + 25)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.energy = _clamp(pet.energy - 15)
        pet.add_xp(XP_PER_ACTION["play"])
        pet.coins += COINS_PER_ACTION["play"]
        pet.save()
        _log(pet, PetActionLog.ACTION_PLAY)
        return pet

    @staticmethod
    @transaction.atomic
    def sleep(user) -> Pet:
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        pet.energy = _clamp(pet.energy + 40)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.add_xp(XP_PER_ACTION["sleep"])
        pet.coins += COINS_PER_ACTION["sleep"]
        pet.save()
        _log(pet, PetActionLog.ACTION_SLEEP)
        return pet

    @staticmethod
    @transaction.atomic
    def heal(user) -> Pet:
        """Revive a fainted or near-dead pet at the cost of HEAL_COST coins."""
        pet = _locked_pet(user)
        if pet.coins < HEAL_COST:
            raise InsufficientCoins()
        pet.apply_decay(save=False)
        pet.coins -= HEAL_COST
        pet.hunger = max(pet.hunger, 50)
        pet.happiness = max(pet.happiness, 50)
        pet.energy = max(pet.energy, 50)
        pet.save()
        _log(pet, PetActionLog.ACTION_HEAL)
        return pet

    @staticmethod
    @transaction.atomic
    def rename(user, new_name: str) -> Pet:
        cleaned = (new_name or "").strip()
        if not cleaned or len(cleaned) > NAME_MAX_LEN:
            raise InvalidName()
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        old = pet.name
        pet.name = cleaned
        pet.save()
        _log(pet, PetActionLog.ACTION_RENAME, detail=f"{old} -> {cleaned}")
        return pet
