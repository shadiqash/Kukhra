from django.contrib import admin

from .models import ProcessingRun


@admin.register(ProcessingRun)
class ProcessingRunAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'lot', 'run_at', 'input_weight_kg', 'output_weight_kg', 'operator')
    list_filter   = ('run_at',)
    search_fields = ('lot__code', 'operator__username')
    readonly_fields = ('created_at', 'updated_at')
