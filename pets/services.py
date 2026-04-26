"""Business logic for pet actions.

Keeping logic in a service layer means views, API endpoints, and admin
actions can all reuse the same rules without duplication.
"""
from .models import Pet


def _clamp(value: int) -> int:
    return max(0, min(Pet.STAT_MAX, value))


class PetService:
    @staticmethod
    def feed(pet: Pet) -> Pet:
        pet.hunger = _clamp(pet.hunger + 25)
        pet.energy = _clamp(pet.energy + 5)
        pet.save()
        return pet

    @staticmethod
    def play(pet: Pet) -> Pet:
        pet.happiness = _clamp(pet.happiness + 25)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.energy = _clamp(pet.energy - 15)
        pet.save()
        return pet

    @staticmethod
    def sleep(pet: Pet) -> Pet:
        pet.energy = _clamp(pet.energy + 40)
        pet.hunger = _clamp(pet.hunger - 10)
        pet.save()
        return pet
