from django.contrib import admin

from .models import Pet


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "hunger", "happiness", "energy", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("owner", "name")}),
        ("Stats", {"fields": ("hunger", "happiness", "energy")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
