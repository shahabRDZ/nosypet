"""Business logic for pet actions.

Keeping logic in a service layer means views, API endpoints, and admin
actions can all reuse the same rules without duplication.
"""
from .models import Pet


XP_PER_ACTION = {"feed": 8, "play": 12, "sleep": 6}
COINS_PER_ACTION = {"feed": 1, "play": 3, "sleep": 1}

# Items the player can buy in the shop. Each item has a cost in coins
# and a dict of stat boosts to apply.
SHOP_ITEMS = {
    "snack": {
        "label": "Tasty Snack",
        "emoji": "🍩",
        "cost": 5,
        "boosts": {"hunger": 35, "happiness": 5},
    },
    "toy": {
        "label": "Squeaky Toy",
        "emoji": "🧸",
        "cost": 8,
        "boosts": {"happiness": 40},
    },
    "potion": {
        "label": "Energy Potion",
        "emoji": "🧪",
        "cost": 12,
        "boosts": {"energy": 60, "happiness": 10},
    },
}


class InsufficientCoins(Exception):
    pass


class UnknownItem(Exception):
    pass


def _clamp(value: int) -> int:
    return max(0, min(Pet.STAT_MAX, value))


def _decayed(pet: Pet) -> Pet:
    pet.apply_decay(save=False)
    return pet


class PetService:
    @staticmethod
    def refresh(pet: Pet) -> Pet:
        pet.apply_decay(save=True)
        return pet

    @staticmethod
    def feed(pet: Pet) -> Pet:
        _decayed(pet)
        pet.hunger = _clamp(pet.hunger + 25)
        pet.energy = _clamp(pet.energy + 5)
        pet.add_xp(XP_PER_ACTION["feed"])
        pet.coins += COINS_PER_ACTION["feed"]
        pet.save()
        return pet

    @staticmethod
    def play(pet: Pet) -> Pet:
        _decayed(pet)
        pet.happiness = _clamp(pet.happiness + 25)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.energy = _clamp(pet.energy - 15)
        pet.add_xp(XP_PER_ACTION["play"])
        pet.coins += COINS_PER_ACTION["play"]
        pet.save()
        return pet

    @staticmethod
    def sleep(pet: Pet) -> Pet:
        _decayed(pet)
        pet.energy = _clamp(pet.energy + 40)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.add_xp(XP_PER_ACTION["sleep"])
        pet.coins += COINS_PER_ACTION["sleep"]
        pet.save()
        return pet

    @staticmethod
    def buy(pet: Pet, item_key: str) -> Pet:
        item = SHOP_ITEMS.get(item_key)
        if item is None:
            raise UnknownItem(item_key)
        if pet.coins < item["cost"]:
            raise InsufficientCoins(item_key)

        _decayed(pet)
        pet.coins -= item["cost"]
        for stat, delta in item["boosts"].items():
            setattr(pet, stat, _clamp(getattr(pet, stat) + delta))
        pet.save()
        return pet
