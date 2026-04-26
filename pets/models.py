from django.conf import settings
from django.db import models
from django.utils import timezone


# Decay rates: stat points lost per minute of real time.
DECAY_PER_MINUTE = {
    "hunger": 0.5,
    "happiness": 0.4,
    "energy": 0.3,
}


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

    last_decay_at = models.DateTimeField(default=timezone.now)
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

    def apply_decay(self, save=True):
        """Drop stats based on minutes elapsed since the last decay tick.

        We compute on read instead of running a background job, so the
        pet ages naturally even when no one is watching.
        """
        now = timezone.now()
        elapsed_minutes = (now - self.last_decay_at).total_seconds() / 60
        if elapsed_minutes <= 0:
            return

        for stat, rate in DECAY_PER_MINUTE.items():
            current = getattr(self, stat)
            decayed = max(0, int(round(current - rate * elapsed_minutes)))
            setattr(self, stat, decayed)

        self.last_decay_at = now
        if save:
            self.save()
