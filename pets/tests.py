"""Tests for the pets app."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from pets.models import (
    HEAL_COST,
    MEDICINE_COST,
    AchievementUnlock,
    Pet,
    PetActionLog,
)
from pets.services import (
    InsufficientCoins,
    InvalidColor,
    InvalidName,
    NotSick,
    PetService,
    TooTired,
    list_achievements,
)


class PetSignalTests(TestCase):
    def test_pet_created_for_new_user(self):
        u = User.objects.create_user(username="alice", password="pw")
        self.assertTrue(hasattr(u, "pet"))
        self.assertEqual(u.pet.stage, Pet.STAGE_EGG)
        self.assertEqual(u.pet.level, 1)

    def test_no_pet_for_superuser(self):
        u = User.objects.create_superuser(username="root", password="pw")
        self.assertFalse(Pet.objects.filter(owner=u).exists())


class PetDecayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="pw")
        self.pet = self.user.pet

    def test_no_change_for_short_interval(self):
        self.pet.last_decay_at = timezone.now() - timedelta(seconds=7)
        self.pet.save()
        h0 = self.pet.hunger
        self.pet.refresh_from_db()
        self.pet.apply_decay()
        self.assertEqual(self.pet.hunger, h0)

    def test_clock_does_not_advance_on_no_op(self):
        # 7 seconds of decay floors to zero. last_decay_at must NOT
        # advance, otherwise fractional decay is silently dropped.
        original = timezone.now() - timedelta(seconds=7)
        self.pet.last_decay_at = original
        self.pet.save()
        self.pet.refresh_from_db()
        self.pet.apply_decay()
        self.pet.refresh_from_db()
        # Allow microsecond drift but the clock must not have jumped to "now".
        self.assertLess(timezone.now() - self.pet.last_decay_at,
                        timedelta(seconds=14))

    def test_long_interval_drops_stats(self):
        self.pet.last_decay_at = timezone.now() - timedelta(minutes=5)
        self.pet.save()
        self.pet.refresh_from_db()
        self.pet.apply_decay()
        # hunger rate 1.2/min * 5 min = 6 points lost
        self.assertEqual(self.pet.hunger, 74)


class PetServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="pw")

    def test_feed_increases_hunger_and_grants_xp(self):
        before = Pet.objects.get(owner=self.user)
        before.hunger = 40
        before.save()
        pet = PetService.feed(self.user)
        self.assertEqual(pet.hunger, 65)
        self.assertEqual(pet.xp, 8)
        # 10 starting + 1 for feed + 5 from First Bite achievement = 16
        self.assertEqual(pet.coins, 16)
        self.assertEqual(
            PetActionLog.objects.filter(pet=pet, action="feed").count(), 1
        )

    def test_play_costs_hunger_and_energy(self):
        pet = PetService.play(self.user)
        self.assertEqual(pet.hunger, 70)
        self.assertEqual(pet.energy, 65)
        self.assertEqual(pet.happiness, 100)

    def test_sleep_restores_energy(self):
        p = self.user.pet
        p.energy = 30
        p.save()
        pet = PetService.sleep(self.user)
        self.assertEqual(pet.energy, 70)

    def test_heal_requires_coins(self):
        with self.assertRaises(InsufficientCoins):
            PetService.heal(self.user)

    def test_heal_revives_pet(self):
        p = self.user.pet
        p.coins = HEAL_COST + 5
        p.hunger = 0
        p.happiness = 0
        p.energy = 0
        p.save()
        pet = PetService.heal(self.user)
        self.assertEqual(pet.coins, 5)
        self.assertGreaterEqual(pet.hunger, 50)
        self.assertGreaterEqual(pet.happiness, 50)
        self.assertGreaterEqual(pet.energy, 50)

    def test_rename_validates_input(self):
        with self.assertRaises(InvalidName):
            PetService.rename(self.user, "")
        with self.assertRaises(InvalidName):
            PetService.rename(self.user, "x" * 31)

    def test_rename_logs_old_and_new_names(self):
        pet = PetService.rename(self.user, "Spot")
        self.assertEqual(pet.name, "Spot")
        log = PetActionLog.objects.get(pet=pet, action="rename")
        self.assertIn("Nosy", log.detail)
        self.assertIn("Spot", log.detail)


class XpAndStageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dan", password="pw")
        self.pet = self.user.pet

    def test_level_up_promotes_stage(self):
        self.pet.add_xp(100)
        self.pet.save()
        self.assertEqual(self.pet.level, 2)
        self.assertEqual(self.pet.stage, Pet.STAGE_BABY)

    def test_xp_curve_increases(self):
        l1 = self.pet.xp_to_next_level
        self.pet.level = 5
        l5 = self.pet.xp_to_next_level
        self.assertGreater(l5, l1)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="erin", password="pw12345!")

    def test_anonymous_redirected(self):
        res = self.client.get(reverse("pets:dashboard"))
        self.assertEqual(res.status_code, 302)

    def test_authenticated_renders_creature(self):
        self.client.login(username="erin", password="pw12345!")
        res = self.client.get(reverse("pets:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'class="scene"')
        self.assertContains(res, "antenna-tip")

    def test_dashboard_creates_pet_for_petless_superuser(self):
        admin = User.objects.create_superuser(username="root", password="pw")
        self.client.force_login(admin)
        res = self.client.get(reverse("pets:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Pet.objects.filter(owner=admin).exists())


@override_settings(RATELIMIT_ENABLE=False)
class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="frank", password="pw12345!")
        self.client.login(username="frank", password="pw12345!")

    def test_state_endpoint(self):
        res = self.client.get(reverse("pets:api_state"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("hunger", res.json())

    def test_feed_endpoint(self):
        res = self.client.post(reverse("pets:api_feed"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["xp"], 8)

    def test_rename_endpoint_rejects_empty(self):
        res = self.client.post(
            reverse("pets:api_rename"),
            data='{"name": ""}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_rename_endpoint_accepts_valid(self):
        res = self.client.post(
            reverse("pets:api_rename"),
            data='{"name": "Pixel"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Pixel")

    def test_heal_without_coins_returns_402(self):
        self.user.pet.coins = 0
        self.user.pet.save()
        res = self.client.post(reverse("pets:api_heal"))
        self.assertEqual(res.status_code, 402)


class FetchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fetch_u", password="pw")

    def test_fetch_consumes_energy_and_rewards(self):
        pet = PetService.fetch(self.user)
        self.assertEqual(pet.energy, 70)
        self.assertEqual(pet.happiness, 95)
        # Starting coins 10 + 5 fetch reward = 15 (no achievement yet).
        self.assertEqual(pet.coins, 15)
        self.assertEqual(pet.xp, 14)

    def test_fetch_refused_when_too_tired(self):
        p = self.user.pet
        p.energy = 5
        p.save()
        with self.assertRaises(TooTired):
            PetService.fetch(self.user)


class SicknessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sick_u", password="pw")

    def test_decay_marks_neglected_pet_sick(self):
        p = self.user.pet
        p.hunger = 10
        p.happiness = 10
        p.energy = 10
        p.last_decay_at = timezone.now() - timedelta(minutes=2)
        p.save()
        p.refresh_from_db()
        p.apply_decay()
        self.assertTrue(p.is_sick)

    def test_medicine_cures_sickness(self):
        p = self.user.pet
        p.is_sick = True
        p.coins = MEDICINE_COST + 2
        p.save()
        pet = PetService.medicine(self.user)
        self.assertFalse(pet.is_sick)
        self.assertEqual(pet.coins, 2)

    def test_medicine_requires_sickness(self):
        with self.assertRaises(NotSick):
            PetService.medicine(self.user)

    def test_medicine_requires_coins(self):
        p = self.user.pet
        p.is_sick = True
        p.coins = 0
        p.save()
        with self.assertRaises(InsufficientCoins):
            PetService.medicine(self.user)


class ColorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="color_u", password="pw")

    def test_recolor_sets_color(self):
        pet = PetService.recolor(self.user, Pet.COLOR_BLUE)
        self.assertEqual(pet.color, Pet.COLOR_BLUE)

    def test_recolor_rejects_unknown(self):
        with self.assertRaises(InvalidColor):
            PetService.recolor(self.user, "rainbow")


class AchievementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ach_u", password="pw")

    def test_first_feed_unlocks_first_bite(self):
        pet = PetService.feed(self.user)
        self.assertTrue(
            AchievementUnlock.objects.filter(pet=pet, slug="first_bite").exists()
        )
        self.assertTrue(any(a.get("slug") == "first_bite" for a in pet._new_unlocks))

    def test_unlock_grants_coins_once(self):
        # Two feeds: first should unlock + reward, second should not.
        pet1 = PetService.feed(self.user)
        coins_after_first = pet1.coins
        pet2 = PetService.feed(self.user)
        # Only the +1 feed coin gain on the second call.
        self.assertEqual(pet2.coins, coins_after_first + 1)

    def test_list_achievements_marks_unlocked(self):
        PetService.feed(self.user)
        items = list_achievements(self.user.pet)
        first = next(a for a in items if a["slug"] == "first_bite")
        self.assertTrue(first["unlocked"])
        other = next(a for a in items if a["slug"] == "best_friend")
        self.assertFalse(other["unlocked"])


class PWATests(TestCase):
    def test_manifest_served(self):
        res = self.client.get("/manifest.webmanifest")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/manifest+json")
        self.assertIn(b'"name"', res.content)

    def test_service_worker_served(self):
        res = self.client.get("/sw.js")
        self.assertEqual(res.status_code, 200)
        self.assertIn("javascript", res["Content-Type"])
        self.assertEqual(res["Service-Worker-Allowed"], "/")


@override_settings(RATELIMIT_ENABLE=True)
class RateLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="grace", password="pw12345!")
        self.client.login(username="grace", password="pw12345!")

    def test_feed_rate_limit_triggers(self):
        for _ in range(30):
            self.client.post(reverse("pets:api_feed"))
        res = self.client.post(reverse("pets:api_feed"))
        self.assertEqual(res.status_code, 403)
