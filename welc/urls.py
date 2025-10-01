from django.urls import path
from .views import (
    LeatherTagsView, GenerateTagsView, PrintTagsView, ExportTagsView,
    UpdatePrintCountView, material_sources_chart, TraceAPI,
    TraderDashboardAPI, TraderTransactionAPI, TanneryDashboardAPI,
    GarmentDashboardAPI, GarmentTransactionAPI, GarmentProductsAPI,
    ValidateStampAPI, PrintGarmentQRAPI, DisplayDataView,
    UserTransactionsAPI, TanneryTransactionsAPI,
)

urlpatterns = [
    path('traceability/leather-tags/', LeatherTagsView.as_view(), name='leather_tags_api'),
    path('tags/<str:tag_id>/', DisplayDataView.as_view(), name='display_data'),
    path('traceability/tag-generations/generate-tags/<int:confirmation_id>/', GenerateTagsView.as_view(),
         name='generate_tags_api'),
    path('traceability/tag-generations/<int:confirmation_id>/print-tags/', PrintTagsView.as_view(),
         name='print_tags_api'),
    path('traceability/export-tags/', ExportTagsView.as_view(), name='export_tags_api'),
    path('traceability/tag-generations/<str:tag_id>/update-print-count/', UpdatePrintCountView.as_view(),
         name='update_print_count_api'),
    path('traceability/material-sources-chart/', material_sources_chart, name='material_sources_chart_api'),

    path('trace/', TraceAPI.as_view({'post': 'create'}), name='trace_api'),

    # Role-specific transaction endpoints
    path('transactions/trader/', TraderTransactionAPI.as_view(), name='trader_transactions'),
    path('transactions/tannery/', TanneryTransactionsAPI.as_view(), name='tannery_transactions'),
    path('transactions/garment/', GarmentTransactionAPI.as_view(), name='garment_transactions'),

    # Generic endpoint (for backward compatibility)
    path('transactions/history/', UserTransactionsAPI.as_view(), name='user_transactions'),

    # Dashboard endpoints
    path('trader/dashboard/', TraderDashboardAPI.as_view(), name='trader_dashboard'),
    path('trader/transaction/', TraderTransactionAPI.as_view(), name='trader_transaction'),
    path('tannery/dashboard/', TanneryDashboardAPI.as_view(), name='tannery_dashboard'),
    path('garment/dashboard/', GarmentDashboardAPI.as_view(), name='garment_dashboard'),
    path('garment/transaction/', GarmentTransactionAPI.as_view(), name='garment_transaction'),
    path('garment/products/', GarmentProductsAPI.as_view(), name='garment_products'),
    path('garment/validate-stamp/', ValidateStampAPI.as_view(), name='validate_stamp'),
    path('garment/print-qr/<str:garment_id>/', PrintGarmentQRAPI.as_view(), name='print_garment_qr'),
]