from django.contrib import admin

from .models import Pet


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = (
        "name", "owner", "stage", "level", "xp",
        "hunger", "happiness", "energy", "updated_at",
    )
    list_filter = ("stage", "level", "created_at")
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at", "last_decay_at")
    fieldsets = (
        ("Identity", {"fields": ("owner", "name")}),
        ("Stats", {"fields": ("hunger", "happiness", "energy")}),
        ("Progress", {"fields": ("stage", "level", "xp")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_decay_at")}),
    )
