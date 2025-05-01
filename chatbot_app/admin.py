from django.contrib import admin
from .models import (
    FAQ, Project, CustomChatbotResponse, CompanyInformation,
    ProductService, PageContent, ChatSession, ChatMessage
)

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'keywords', 'last_updated')
    list_filter = ('category',)
    search_fields = ('question', 'answer', 'keywords')

@admin.register(CustomChatbotResponse)
class CustomChatbotResponseAdmin(admin.ModelAdmin):
    list_display = ('keywords_preview', 'response_preview', 'priority', 'is_active', 'project', 'created_by', 'last_updated')
    list_filter = ('is_active', 'priority', 'project', 'created_by')
    search_fields = ('keywords', 'response')
    raw_id_fields = ('project', 'created_by')
    list_editable = ('priority', 'is_active')
    
    def keywords_preview(self, obj):
        return obj.keywords[:50] + "..." if len(obj.keywords) > 50 else obj.keywords
    keywords_preview.short_description = "Keywords"
    
    def response_preview(self, obj):
        return obj.response[:50] + "..." if len(obj.response) > 50 else obj.response
    response_preview.short_description = "Response"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'end_date', 'last_updated')
    list_filter = ('status',)
    search_fields = ('name', 'description', 'keywords')
    list_editable = ('status',)

@admin.register(CompanyInformation)
class CompanyInformationAdmin(admin.ModelAdmin):
    list_display = ('title', 'keywords_preview', 'last_updated')
    search_fields = ('title', 'content', 'keywords')
    
    def keywords_preview(self, obj):
        return obj.keywords[:50] + "..." if len(obj.keywords) > 50 else obj.keywords
    keywords_preview.short_description = "Keywords"

@admin.register(ProductService)
class ProductServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'last_updated')
    list_filter = ('category',)
    search_fields = ('name', 'description', 'features', 'keywords')

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_path', 'section', 'page_category', 'priority', 'last_updated')
    list_filter = ('page_category', 'priority')
    search_fields = ('title', 'content', 'keywords', 'page_path')
    list_editable = ('priority',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'created_at', 'last_interaction', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('session_id', 'user__email')
    readonly_fields = ('session_id', 'created_at', 'last_interaction')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'is_bot', 'message_preview', 'timestamp')
    list_filter = ('is_bot', 'timestamp')
    search_fields = ('message', 'session__session_id')
    readonly_fields = ('timestamp',)
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Message" 