from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from pets.models import Pet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_pet_for_new_user(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        Pet.objects.create(owner=instance)
