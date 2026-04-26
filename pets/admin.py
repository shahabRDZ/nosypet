from django.contrib import admin

from .models import Pet, PetActionLog


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = (
        "name", "owner", "stage", "level", "xp",
        "hunger", "happiness", "energy", "coins", "updated_at",
    )
    list_filter = ("stage", "level", "created_at")
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at", "last_decay_at")
    fieldsets = (
        ("Identity", {"fields": ("owner", "name")}),
        ("Stats", {"fields": ("hunger", "happiness", "energy")}),
        ("Progress", {"fields": ("stage", "level", "xp", "coins")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_decay_at")}),
    )


@admin.register(PetActionLog)
class PetActionLogAdmin(admin.ModelAdmin):
    list_display = ("pet", "action", "detail", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("pet__name", "pet__owner__username", "detail")
    readonly_fields = ("pet", "action", "detail", "created_at")
    date_hierarchy = "created_at"
