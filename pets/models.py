from django.conf import settings
from django.db import models
from django.utils import timezone

# Decay rates: stat points lost per minute of real time.
# Tuned so an idle pet hits "low" mood in roughly 1-2 hours and
# zero in 3-4 hours, giving the player a real reason to return.
DECAY_PER_MINUTE = {
    "hunger": 1.2,
    "happiness": 0.9,
    "energy": 0.7,
}

# Cost (in coins) to revive a fainted or near-dead pet back to 50 in
# all three stats. Picked so the player needs ~7-10 happy actions to
# afford a heal, making it a meaningful safety net rather than free.
HEAL_COST = 20


class Pet(models.Model):
    """A virtual pet owned by a user. Stats range 0 to 100 (higher is better)."""

    STAT_MAX = 100

    STAGE_EGG = "egg"
    STAGE_BABY = "baby"
    STAGE_TEEN = "teen"
    STAGE_ADULT = "adult"
    STAGE_CHOICES = [
        (STAGE_EGG, "Egg"),
        (STAGE_BABY, "Baby"),
        (STAGE_TEEN, "Teen"),
        (STAGE_ADULT, "Adult"),
    ]

    # Level threshold for moving up a life stage.
    STAGE_THRESHOLDS = [
        (1, STAGE_EGG),
        (2, STAGE_BABY),
        (5, STAGE_TEEN),
        (10, STAGE_ADULT),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pet",
    )
    name = models.CharField(max_length=30, default="Nosy")

    hunger = models.PositiveSmallIntegerField(default=80)
    happiness = models.PositiveSmallIntegerField(default=80)
    energy = models.PositiveSmallIntegerField(default=80)

    level = models.PositiveSmallIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    coins = models.PositiveIntegerField(default=10)
    stage = models.CharField(max_length=10, choices=STAGE_CHOICES, default=STAGE_EGG)

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

    @property
    def xp_to_next_level(self):
        # Exponential-ish curve: level 1 -> 100, 2 -> 175, 3 -> 270, etc.
        # Slows down so reaching adult stage takes real engagement.
        return int(100 * (1.5 ** (self.level - 1)))

    def add_xp(self, amount: int):
        """Grant XP and handle level-ups + stage transitions."""
        self.xp += amount
        levels_gained = 0
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            levels_gained += 1
        if levels_gained:
            self._update_stage()
        return levels_gained

    def _update_stage(self):
        new_stage = self.stage
        for threshold, stage in self.STAGE_THRESHOLDS:
            if self.level >= threshold:
                new_stage = stage
        self.stage = new_stage

    def apply_decay(self, save=True):
        """Drop stats based on minutes elapsed since the last decay tick.

        Uses floor so frequent polls do not silently round fractional
        decay to zero. Only advances ``last_decay_at`` when a stat
        actually changed; otherwise the elapsed time accumulates until
        the decay reaches a whole point.
        """
        now = timezone.now()
        elapsed_minutes = (now - self.last_decay_at).total_seconds() / 60
        if elapsed_minutes <= 0:
            return

        any_changed = False
        for stat, rate in DECAY_PER_MINUTE.items():
            current = getattr(self, stat)
            # Floor the decay amount itself so fractional decay never
            # rounds a stat down by 1 spuriously (e.g. int(79.99) == 79).
            decay_amount = int(rate * elapsed_minutes)
            if decay_amount <= 0:
                continue
            decayed = max(0, current - decay_amount)
            if decayed != current:
                setattr(self, stat, decayed)
                any_changed = True

        if any_changed:
            self.last_decay_at = now
            if save:
                self.save()


class PetActionLog(models.Model):
    """Audit trail of every action taken on a pet. Useful for analytics
    and for showing the player a recent activity feed."""

    ACTION_FEED = "feed"
    ACTION_PLAY = "play"
    ACTION_SLEEP = "sleep"
    ACTION_HEAL = "heal"
    ACTION_RENAME = "rename"
    ACTION_CHOICES = [
        (ACTION_FEED, "Feed"),
        (ACTION_PLAY, "Play"),
        (ACTION_SLEEP, "Sleep"),
        (ACTION_HEAL, "Heal"),
        (ACTION_RENAME, "Rename"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="actions")
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["pet", "-created_at"])]

    def __str__(self):
        return f"{self.pet.name} · {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
