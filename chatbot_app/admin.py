from django.contrib import admin
from .models import FAQ

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'keywords', 'last_updated')
    list_filter = ('category',)
    search_fields = ('question', 'answer', 'keywords') 