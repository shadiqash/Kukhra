from django.contrib import admin

from .models import Counter, Location


class CounterInline(admin.TabularInline):
    model  = Counter
    extra  = 0
    fields = ('name',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'type', 'lat', 'lng')
    list_filter   = ('type',)
    search_fields = ('name',)
    inlines       = [CounterInline]


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display  = ('name', 'location')
    list_filter   = ('location__type',)
    search_fields = ('name', 'location__name')
