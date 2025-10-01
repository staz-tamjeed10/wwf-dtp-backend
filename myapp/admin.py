from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'full_name', 'contact_person', 'contact_no', 'brand', 'registered_since', 'business_type', 'leather_types', 'animal_types', 'city','location', 'operation_type','certifications','time_stamp', 'email_verified', 'verification_token', 'token_created_at')  # Fields to display in the list view
    list_filter = ('email_verified', 'role', 'city','time_stamp')  # Filters on the right sidebar
    search_fields = ('user__username', 'full_name', 'contact_no', 'business_type', 'city')  # Search bar for these fields
    ordering = ('user',)  # Default sorting order
