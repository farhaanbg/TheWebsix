from django.contrib import admin
from .models import Hike


@admin.register(Hike)
class HikeAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'difficulty', 'price', 'capacity', 'reserved_spots')
    list_filter = ('difficulty', 'date', 'district')
    search_fields = ('title', 'location', 'district', 'guide')
    date_hierarchy = 'date'
