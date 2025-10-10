from django.contrib.gis.admin import GISModelAdmin
from django.contrib import admin
from .models import Issue, Category, IssuePhoto

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Issue)
class IssueAdmin(GISModelAdmin):
    list_display = ('title', 'status', 'category', 'reporter', 'assigned_to')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    raw_id_fields = ('reporter', 'assigned_to')

    # Spatial admin settings
    map_template = 'gis/admin/openlayers.html'
    default_lat = 40.7128  # New York
    default_lon = -74.0060
    default_zoom = 12

@admin.register(IssuePhoto)
class IssuePhotoAdmin(admin.ModelAdmin):
    list_display = ('issue', 'caption', 'uploaded_at')
    raw_id_fields = ('issue',)