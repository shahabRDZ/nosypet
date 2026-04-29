"""Business logic for pet actions.

Each mutation runs in a database transaction with `select_for_update`
on the pet row, so two concurrent requests from the same user cannot
race each other into a lost update. Every action also writes a
PetActionLog row for analytics and for the recent-activity feed.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import (
    ACHIEVEMENT_BY_SLUG,
    HEAL_COST,
    MEDICINE_COST,
    AchievementUnlock,
    Pet,
    PetActionLog,
)

User = get_user_model()

XP_PER_ACTION = {"feed": 8, "play": 12, "sleep": 6, "fetch": 14}
COINS_PER_ACTION = {"feed": 1, "play": 3, "sleep": 1, "fetch": 5}
NAME_MAX_LEN = 30
FETCH_ENERGY_COST = 10
FETCH_HAPPINESS_GAIN = 15
FETCH_MIN_ENERGY = 15


class InsufficientCoins(Exception):
    pass


class InvalidName(Exception):
    pass


class TooTired(Exception):
    pass


class NotSick(Exception):
    pass


class InvalidColor(Exception):
    pass


def _clamp(value: int) -> int:
    return max(0, min(Pet.STAT_MAX, value))


def _locked_pet(user) -> Pet:
    """Fetch the user's pet with a row-level lock for the rest of the txn."""
    return Pet.objects.select_for_update().get(owner=user)


def _log(pet: Pet, action: str, detail: str = "") -> None:
    PetActionLog.objects.create(pet=pet, action=action, detail=detail)


# Maps each achievement slug to a (action_filter, threshold) pair.
# We count actions with .filter(action=...) rather than running the
# check inline so adding a new achievement is a one-liner.
ACHIEVEMENT_TRIGGERS = {
    "first_bite": (PetActionLog.ACTION_FEED, 1),
    "best_friend": (PetActionLog.ACTION_PLAY, 10),
    "sweet_dreams": (PetActionLog.ACTION_SLEEP, 10),
}


def _check_achievements(pet: Pet) -> list[dict]:
    """Award any newly-earned achievements. Returns list of unlock dicts.

    Called inside the action transaction so the unlock row and the coin
    reward commit together with the action that earned them.
    """
    already = set(
        AchievementUnlock.objects.filter(pet=pet).values_list("slug", flat=True)
    )
    newly = []
    for slug, (action, threshold) in ACHIEVEMENT_TRIGGERS.items():
        if slug in already:
            continue
        count = PetActionLog.objects.filter(pet=pet, action=action).count()
        if count >= threshold:
            AchievementUnlock.objects.create(pet=pet, slug=slug)
            meta = ACHIEVEMENT_BY_SLUG[slug]
            pet.coins += meta["reward_coins"]
            newly.append(meta)
    if newly:
        pet.save(update_fields=["coins"])
    return newly


def list_achievements(pet: Pet) -> list[dict]:
    unlocked = set(
        AchievementUnlock.objects.filter(pet=pet).values_list("slug", flat=True)
    )
    return [
        {**a, "unlocked": a["slug"] in unlocked}
        for a in ACHIEVEMENT_BY_SLUG.values()
    ]


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
        pet._new_unlocks = _check_achievements(pet)
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
        pet._new_unlocks = _check_achievements(pet)
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
        pet._new_unlocks = _check_achievements(pet)
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
    def fetch(user) -> Pet:
        """Play fetch: a higher-reward variant of play, gated on energy.

        Costs more energy than play and refuses to start if the pet is
        too tired — this stops the player from chaining fetch into the
        ground while still keeping it the most lucrative interaction.
        """
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        if pet.energy < FETCH_MIN_ENERGY:
            raise TooTired()
        pet.energy = _clamp(pet.energy - FETCH_ENERGY_COST)
        pet.happiness = _clamp(pet.happiness + FETCH_HAPPINESS_GAIN)
        pet.hunger = _clamp(pet.hunger - 5)
        pet.add_xp(XP_PER_ACTION["fetch"])
        pet.coins += COINS_PER_ACTION["fetch"]
        pet.save()
        _log(pet, PetActionLog.ACTION_FETCH)
        return pet

    @staticmethod
    @transaction.atomic
    def medicine(user) -> Pet:
        """Cure sickness. Cheaper than a full heal because it does not
        also restore stats — sickness is just a debuff flag."""
        pet = _locked_pet(user)
        if not pet.is_sick:
            raise NotSick()
        if pet.coins < MEDICINE_COST:
            raise InsufficientCoins()
        pet.apply_decay(save=False)
        pet.coins -= MEDICINE_COST
        pet.is_sick = False
        pet.save()
        _log(pet, PetActionLog.ACTION_MEDICINE)
        return pet

    @staticmethod
    @transaction.atomic
    def recolor(user, color: str) -> Pet:
        if color not in dict(Pet.COLOR_CHOICES):
            raise InvalidColor()
        pet = _locked_pet(user)
        pet.apply_decay(save=False)
        pet.color = color
        pet.save()
        _log(pet, PetActionLog.ACTION_RECOLOR, detail=color)
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
