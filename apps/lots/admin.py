from django.contrib import admin

from .models import Lot


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display  = ('code', 'source_type', 'supplier', 'arrival_location', 'bird_count', 'live_weight_kg', 'status')
    list_filter   = ('source_type', 'status', 'arrival_location')
    search_fields = ('code',)
    readonly_fields = ('created_at', 'updated_at')
