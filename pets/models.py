from django.conf import settings
from django.db import models


class Pet(models.Model):
    """A virtual pet owned by a user. Stats range 0 to 100 (higher is better)."""

    STAT_MAX = 100

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pet",
    )
    name = models.CharField(max_length=30, default="Nosy")

    hunger = models.PositiveSmallIntegerField(default=80)
    happiness = models.PositiveSmallIntegerField(default=80)
    energy = models.PositiveSmallIntegerField(default=80)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    @property
    def is_alive(self):
        return self.hunger > 0 and self.happiness > 0 and self.energy > 0

    @property
    def overall_score(self):
        return (self.hunger + self.happiness + self.energy) // 3
