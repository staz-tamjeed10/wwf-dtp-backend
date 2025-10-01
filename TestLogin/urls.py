from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Your app's API urls
    path('api/auth/', include('myapp.urls')),
    path('api/', include('welc.urls')),

    # API schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Optional: Swagger UI
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Optional: Redoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# from django.urls import path, include
# from django.contrib import admin
# from myapp.views import (
#     home_view, login_view, register_view, profile_view,
#     edit_profile_view, logout_view, contact_view, service_view, activate,
#     CustomPasswordResetView, CustomPasswordResetConfirmView, about_view
# )
# from welc.views import WelcomeView, DisplayDataView, SearchDataView, trader_view, tannery_view, validate_stamp, garment_view, leather_tags_view, generate_tags, print_tags, update_print_count, export_generated_tags_csv, garment_products, print_garment_qr, garment_detail, check_tags_api, check_tag_status, check_tag_arrived
# from qrcode_data.views import view_qr_codes, edit_qr_code, delete_qr_code, print_single_tag
# from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView
# from welc.views import material_sources_chart
# urlpatterns = [
#     path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
#     path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
#     path('admin/', admin.site.urls),  # Include the admin URLs
#     path('material-sources-chart/', material_sources_chart, name='material_sources_chart'),
#     path('', home_view, name='home'),
#     path('contact/', contact_view, name='contact'),
#     path('services/', service_view, name='service'),
#     path('about/', about_view, name='about'),
#     path('login/', login_view, name='login'),
#     path('register/', register_view, name='register'),
#     path('profile/', profile_view, name='profile'),
#     path('logout/', logout_view, name='logout'),
#     # Role-based views
#     path('profile/edit/', edit_profile_view, name='edit_profile'),
#     path('welcome/', WelcomeView.as_view(), name='welcome'),
#     path("search/", SearchDataView.as_view(), name="search"),
#     path('camera_feed/', SearchDataView.as_view(), name='camera_feed'),
#     path('trader/', trader_view, name='trader'),  # Corrected the name to 'trader_view'
#     path('tannery/', tannery_view, name='tannery'),  # Corrected the name to 'tannery_view',
#     path('garment/', garment_view, name='garment'),
#     path('garment-products/', garment_products, name='garment_products'),
#     path('garment/<str:garment_id>/', garment_detail, name='garment_detail'),
#     path('print-garment/<str:garment_id>/', print_garment_qr, name='print_garment_qr'),
#     path('check-tag-status/<str:tag_id>/', check_tag_status, name='check_tag_status'),
#     path('api/tag-arrived/<str:tag_id>/', check_tag_arrived, name='check_tag_arrived'),
#     path('validate-stamp/', validate_stamp, name='validate_stamp'),
#     path("leather-tags/", leather_tags_view, name="leather_tags"),
#     path('generate-tags/<int:confirmation_id>/', generate_tags, name="generate_tags"),
#     path('print-tags/<int:confirmation_id>/', print_tags, name="print_tags"),
#     path("update-print-count/<str:tag_id>/", update_print_count, name="update_print_count"),
#     path('export-tags/', export_generated_tags_csv, name='export_tags_csv'),
#     path('api/check-tags/', check_tags_api, name='check_tags_api'),
#
#     # Path for viewing QR codes
#     path('view_qr_codes/', view_qr_codes, name='view_qr_codes'),
#     # urls.py
#     path('edit-qr/<str:new_tag>/', edit_qr_code, name='edit_qr_code'),
#     path('print_tag/<str:new_tag>/', print_single_tag, name='print_tag'),
#     path('delete-qr/<str:new_tag>/', delete_qr_code, name='delete_qr_code'),
#
#     path('view-data/<str:new_tag>/', DisplayDataView.as_view(), name='display_data'),
#
#     # Account activation and password reset paths
#     path('activate/<uidb64>/<token>/', activate, name='activate'),
#     path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
#     path('password_reset/done/', PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
#     path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
#     path('reset/done/', PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
# ]
