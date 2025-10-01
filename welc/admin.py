# admins.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Tannery, TransactionLog, TagGeneration, GarmentProduct
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django.utils import timezone

class TraderInline(admin.TabularInline):
    model = TagGeneration.traders.through
    extra = 1
    verbose_name = "Trader"
    raw_id_fields = ('user',)

class ProductTypeFilter(admin.SimpleListFilter):
    title = 'Product Type'
    parameter_name = 'product_types'

    def lookups(self, request, model_admin):
        return TagGeneration.PRODUCT_TYPE_CHOICES  # Updated to use TagGeneration's choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(product_types__contains=self.value())
        return queryset

@admin.register(GarmentProduct)
class GarmentProductAdmin(admin.ModelAdmin):
    list_display = ('garment_id', 'user', 'g_date', 'num_pieces','product_types','other_product_type', 'brand', 'tags_list','time_stamp')
    list_filter = ('user', 'g_date')
    search_fields = ('garment_id', 'brand', 'tags__new_tag')
    readonly_fields = ('garment_id',)

    def tags_list(self, obj):
        # Access tags via the reverse ForeignKey relation 'tags'
        tags = obj.tags.all().order_by('new_tag').values_list('new_tag', flat=True)
        return ", ".join(tags[:5]) + ("..." if tags.count() > 5 else "")
    tags_list.short_description = 'Component Tags'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')

@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('timestamp', 'actor_type', 'action', 'user', 'tag_link', 'tannery_stamp_code_link','garment_link')
    search_fields = ['garment_product__garment_id', 'new_tag__new_tag', 'user__username']
    list_filter = ('action', 'actor_type', 'timestamp')
    readonly_fields = ('formatted_timestamp',)

    def tag_link(self, obj):
        if obj.new_tag:
            url = reverse('admin:welc_taggeneration_change', args=[obj.new_tag.new_tag])
            return format_html('<a href="{}">{}</a>', url, obj.new_tag.new_tag)
        return "-"
    tag_link.short_description = 'Related Tag'
    def tannery_stamp_code_link(self, obj):
        if obj.new_tag and obj.new_tag.tannery_stamp_code:
            url = reverse('admin:welc_taggeneration_change', args=[obj.new_tag.tannery_stamp_code])
            return format_html('<a href="{}">{}</a>', url, obj.new_tag.tannery_stamp_code)
        return "-"
    tannery_stamp_code_link.short_description = 'Related Tannery Stamp'
    # admin.py (TransactionLogAdmin)
    def garment_link(self, obj):
        if obj.new_tag and obj.new_tag.garment_product:
            try:
                url = reverse(
                    'admin:welc_garmentproduct_change',
                    args=[obj.new_tag.garment_product.garment_id]
                )
                return format_html('<a href="{}">{}</a>', url, obj.new_tag.garment_product.garment_id)
            except Exception as e:
                return format_html('<span style="color: red">ERROR: {}</span>', str(e))
        return "-"

    garment_link.short_description = 'Garment Product'

    def formatted_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    formatted_timestamp.short_description = 'Timestamp'

@admin.register(TagGeneration)
class TagGenerationAdmin(admin.ModelAdmin):
    list_display = ('new_tag', 'garment_link', 'old_tag', 'dispatch_status','hide_source','tannery_stamp_code','vehicle_number','trader_name','processed_lot_number', 'article', 'tannage_type', 'dispatch_to', 'product_types','other_product_type', 'brand','g_date','time_stamp')
    search_fields = ('new_tag', 'old_tag', 'garment_product__garment_id')
    list_filter = (
        'garment_dispatched',
        ('garment_product', RelatedDropdownFilter),
        'hide_source',
        'product_code'
    )
    readonly_fields = ('new_tag',)
    fieldsets = (
        ('Identification', {
            'fields': ('new_tag', 'old_tag', 'garment_product')
        }),
        ('Production Details', {
            'fields': ('batch_no', 'total_animals', 'product_code', 'hide_source')
        }),
        ('Timeline', {
            'fields': (
                ('trader_arrived', 'trader_dispatched'),
                ('tannery_arrived', 'tannery_dispatched'),
                ('garment_arrived', 'garment_dispatched')
            )
        }),
        ('Product Info', {
            'fields': ('product_types', 'brand', 'other_product_type', 'g_date')
        }),
        ('Financials', {
            'fields': ('rate', 'price', 'total_tags', 'total_prints')
        }),
    )
    inlines = [TraderInline]  # Add TraderInline for managing traders

    def garment_link(self, obj):
        if obj.garment_product:
            url = reverse('admin:welc_garmentproduct_change', args=[obj.garment_product.garment_id])
            return format_html('<a href="{}">{}</a>', url, obj.garment_product.garment_id)
        return "N/A"
    garment_link.short_description = 'Garment Product'
    garment_link.admin_order_field = 'garment_product__garment_id'

    def dispatch_status(self, obj):
        if obj.garment_dispatched:
            return format_html('<span style="color: green;">✓ Dispatched</span>')
        return format_html('<span style="color: red;">⌛ Pending</span>')
    dispatch_status.short_description = 'Dispatch Status'


# @admin.register(Hd)
# class HdAdmin(admin.ModelAdmin):
#     list_display = [
#         'animal_id', 'tag_id', 'tannery_stamp_code', 'owner','Supplier_id', 'animal_type', 'slaughter_date',
#         'hide_source', 'leather_type', 'origin', 'vehicle_number', 'trader_name','processed_lot_number',
#         'get_product_types', 'brand', 'g_date',
#         'trader_arrived', 'trader_dispatched', 'tannery_arrived', 'tannery_dispatched',
#         'garment_arrived', 'garment_dispatched', 'dispatch_to'
#     ]
#     list_filter = [
#         'hide_source',
#         'leather_type',
#         ('tannery', RelatedDropdownFilter),
#         ProductTypeFilter
#     ]
#     search_fields = [
#         'animal_id', 'tag_id', 'owner', 'Supplier_id',
#         'tannery_stamp_code', 'brand'
#     ]
#     raw_id_fields = ('tannery',)
#     readonly_fields = ('animal_id', 'leather_type')
#     fieldsets = (
#         ("Basic Information", {
#             'fields': (
#                 'animal_id', 'tag_id', 'owner', 'Supplier_id',
#                 'animal_type', 'slaughter_date'
#             )
#         }),
#         ("Product Details", {
#             'fields': (
#                 'leather_type', 'origin', 'hide_source',
#                 'tannery_stamp_code'
#             )
#         }),
#         ("Garment Info", {
#             'fields': (
#                 'product_types', 'other_product_type', 'brand'
#             )
#         }),
#         ("Timestamps", {
#             'fields': (
#                 ('trader_arrived', 'trader_dispatched'),
#                 ('tannery_arrived', 'tannery_dispatched'),
#                 ('garment_arrived', 'garment_dispatched')
#             )
#         }),
#         ("Relationships", {
#             'fields': (
#                 'traders', 'tannery'
#             )
#         }),
#     )
#     inlines = [TraderInline]
#     filter_horizontal = ('traders',)
#     ordering = ('-slaughter_date',)

#     def get_product_types(self, obj):
#         return ", ".join(obj.get_product_types_list()) if obj.product_types else "-"
#     get_product_types.short_description = "Product Types"
