from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from rest_framework import viewsets
from .models import (
    Tannery, Hd, MemberAccountType, OffalCollector, Member,
    CashEntry,
)
import logging
from .serializers import (
    TannerySerializer, HdSerializer, MemberAccountTypeSerializer,
    OffalCollectorSerializer, MemberSerializer, CashEntrySerializer, TagSerializer,
)
logger = logging.getLogger(__name__)
from .models import (
    Confirmation, Tag
)
from .serializers import (
    ConfirmationSerializer
)
from django.core.exceptions import ValidationError
from django.db import connections
from datetime import datetime
import pytz
from .serializers import LeatherTagSerializer
from django.utils.crypto import get_random_string
from django.db import transaction
import csv
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from .models import GarmentProduct
from .serializers import (
    TagGenerationSerializer,
    GarmentProductSerializer,
    TransactionLogSerializer
)
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import TagGeneration, TransactionLog
from myapp.models import Profile
from myapp.serializers import ProfileSerializer
from django.urls import reverse
from io import BytesIO
import qrcode
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import logging
logger = logging.getLogger(__name__)


class TanneryViewSet(viewsets.ModelViewSet):
    queryset = Tannery.objects.all()
    serializer_class = TannerySerializer
    permission_classes = [IsAuthenticated]


class HdViewSet(viewsets.ModelViewSet):
    queryset = Hd.objects.all()
    serializer_class = HdSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MemberAccountTypeViewSet(viewsets.ModelViewSet):
    queryset = MemberAccountType.objects.all()
    serializer_class = MemberAccountTypeSerializer
    permission_classes = [IsAuthenticated]


class OffalCollectorViewSet(viewsets.ModelViewSet):
    queryset = OffalCollector.objects.all()
    serializer_class = OffalCollectorSerializer
    permission_classes = [IsAuthenticated]


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated]


class CashEntryViewSet(viewsets.ModelViewSet):
    queryset = CashEntry.objects.all()
    serializer_class = CashEntrySerializer
    permission_classes = [IsAuthenticated]


class ConfirmationViewSet(viewsets.ModelViewSet):
    queryset = Confirmation.objects.all()
    serializer_class = ConfirmationSerializer
    permission_classes = [IsAuthenticated]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class GarmentProductViewSet(viewsets.ModelViewSet):
    queryset = GarmentProduct.objects.all()
    serializer_class = GarmentProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LeatherTagsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        selected_date_str = request.query_params.get("date", None)
        filter_type = request.query_params.get("filter_type", "all")
        username_query = request.query_params.get("username", "").strip()
        batch_no_query = request.query_params.get("batch_no", "").strip()

        # Parse date
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            except ValueError:
                selected_date = timezone.localtime(timezone.now()).date()
        else:
            selected_date = timezone.localtime(timezone.now()).date()

        # Fetch data from external database
        try:
            with connections['pamco'].cursor() as cursor:
                # Fetch confirmations for the selected date
                confirmations = Confirmation.objects.using('pamco').filter(
                    datetime__date=selected_date
                ).select_related(
                    "cash_entry",
                    "cash_entry__member",
                    "cash_entry__offal_collector",
                    "cash_entry__member__account_type"
                ).order_by("-datetime")

                existing_tags = set(TagGeneration.objects.values_list("confirmation", flat=True))

                data = []
                for confirm in confirmations:
                    cash_entry = confirm.cash_entry
                    member = cash_entry.member
                    offal_collector = cash_entry.offal_collector
                    account_type = member.account_type.type if member.account_type else "N/A"
                    prints_counter = confirm.prints_counter

                    # Convert datetime to local timezone
                    local_datetime = timezone.localtime(confirm.datetime)
                    product_code = cash_entry.command or "N/A"
                    total_tags = 0
                    if product_code.startswith("B"):
                        total_tags = cash_entry.total_animals * 4
                    elif product_code.startswith("M"):
                        total_tags = cash_entry.total_animals * 1

                    # Apply filters
                    if filter_type == "M" and not product_code.startswith("M"):
                        continue
                    elif filter_type == "B" and not product_code.startswith("B"):
                        continue

                    if username_query and username_query.lower() not in member.owner_name.lower():
                        continue

                    if batch_no_query and batch_no_query.lower() not in member.old_batch_no.lower():
                        continue

                    tag_ids = []
                    if str(confirm.id) in existing_tags:
                        tag_ids = list(
                            TagGeneration.objects.filter(confirmation=confirm.id).values_list("new_tag", flat=True)
                        )

                    row_data = {
                        "s_no": confirm.id,
                        "batch_no": member.old_batch_no,
                        "total_animals": cash_entry.total_animals,
                        "command": cash_entry.command or "N/A",
                        "price": cash_entry.price,
                        "amount": cash_entry.amount,
                        "owner_name": member.owner_name,
                        "expiry_days": member.expiry_days,
                        "account_type": account_type,
                        "offal_collector": offal_collector.name if offal_collector else "N/A",
                        "datetime": local_datetime.strftime("%Y-%m-%d %I:%M:%S %p"),
                        "product_code": cash_entry.command or "N/A",
                        "rate": cash_entry.price,
                        "total_tags": total_tags,
                        "total_prints": prints_counter or 0,
                        "print_on_roll": False,
                        "tags_generated": str(confirm.id) in existing_tags,
                        "tag_ids": tag_ids,
                    }
                    data.append(row_data)

                serializer = LeatherTagSerializer(data, many=True)
                return Response({
                    "data": serializer.data,
                    "selected_date": selected_date.strftime("%Y-%m-%d"),
                    "filter_type": filter_type,
                    "username_query": username_query,
                    "batch_no_query": batch_no_query,
                })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateTagsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, confirmation_id):
        try:
            logger.info(f"Attempting to generate tags for confirmation: {confirmation_id}")

            # Fetch confirmation from the 'pamco' database
            confirm = Confirmation.objects.using('pamco').select_related(
                "cash_entry",
                "cash_entry__member",
                "cash_entry__offal_collector",
                "cash_entry__member__account_type"
            ).get(id=confirmation_id)
            logger.info(f"Found confirmation: {confirm.id}")

            tag = Tag.objects.using("pamco").filter(confirmation_id=confirm.id)
            logger.info(f"Found {tag.count()} tags for this confirmation")

            if not tag.exists():
                logger.error("No tags found for this confirmation")
                return Response({"error": "No tags found for this confirmation"},
                                status=status.HTTP_400_BAD_REQUEST)

            cash_entry = confirm.cash_entry
            member = cash_entry.member
            offal_collector = cash_entry.offal_collector
            account_type = member.account_type.type if member.account_type else "N/A"
            prints_counter = confirm.prints_counter

            local_datetime = timezone.localtime(confirm.datetime)
            product_code = cash_entry.command or "N/A"
            total_tags = 0
            if product_code.startswith("B"):
                total_tags = cash_entry.total_animals * 4
            elif product_code.startswith("M"):
                total_tags = cash_entry.total_animals * 1

            current_time = timezone.now()
            generated_tags = []

            with transaction.atomic():
                for t in tag:
                    new_tag = get_random_string(8, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                    row_data = {
                        "user": request.user,
                        "new_tag": new_tag,
                        "old_tag": t.tag,
                        "confirmation": confirm.id,
                        "batch_no": member.old_batch_no,
                        "total_animals": cash_entry.total_animals,
                        "command": cash_entry.command or "N/A",
                        "price": cash_entry.price,
                        "amount": cash_entry.amount,
                        "owner_name": member.owner_name,
                        "expiry_days": member.expiry_days,
                        "account_type": account_type,
                        "offal_collector": offal_collector.name if offal_collector else "N/A",
                        "datetime": local_datetime,
                        "product_code": cash_entry.command or "N/A",
                        "rate": cash_entry.price,
                        "total_tags": total_tags,
                        "total_prints": prints_counter or 0,
                        "time_stamp": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    }

                    tag_instance = TagGeneration.objects.create(**row_data)
                    generated_tags.append(tag_instance.new_tag)

                    # Log transaction for each generated tag
                    TransactionLog.objects.create(
                        new_tag=tag_instance,
                        user=request.user,
                        action="data_entered",
                        actor_type="Slaughterhouse",
                        timestamp=current_time.strftime('%Y-%m-%d %H:%M:%S')
                    )
                logger.info(f"Successfully generated {len(generated_tags)} tags")

            return Response({
                "success": True,
                "message": f"Successfully generated {len(generated_tags)} tags",
                "generated_tags": generated_tags
            })

        except Confirmation.DoesNotExist:
            logger.error(f"Confirmation {confirmation_id} not found in pamco database")
            return Response({"error": "Confirmation ID does not exist in the pamco database."},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating tags: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DisplayDataView(APIView):
    permission_classes = []  # No authentication required

    def get(self, request, tag_id):
        try:
            # First try to find by new_tag (8 digit code)
            tag = TagGeneration.objects.get(new_tag=tag_id)
        except TagGeneration.DoesNotExist:
            try:
                # If not found by new_tag, try by tannery_stamp_code
                tag = TagGeneration.objects.get(tannery_stamp_code=tag_id)
            except TagGeneration.DoesNotExist:
                return Response(
                    {"error": f"No results found for: {tag_id}"},
                    status=status.HTTP_404_NOT_FOUND
                )

        response_data = {
            "type": "tag",
            "id": tag.new_tag,
            "data": TagGenerationSerializer(tag).data,
            "transactions": TransactionLogSerializer(
                tag.transaction_logs.all().order_by('timestamp'),
                many=True
            ).data
        }

        if tag.garment_product:
            response_data["garment"] = GarmentProductSerializer(tag.garment_product).data

        return Response(response_data)


class PrintTagsView(APIView):
    permission_classes = []  # No authentication required

    def generate_qr_code(self, data):
        """Generates QR code and returns it as PIL Image object."""
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        return img

    def get(self, request, confirmation_id):
        try:
            # Get tags for this confirmation
            tags = TagGeneration.objects.filter(confirmation=confirmation_id)
            if not tags.exists():
                return Response(
                    {"error": "No tags found for this confirmation"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create PDF buffer
            buffer = BytesIO()

            # Page size (30mm x 150mm)
            page_width = 30 * 2.83  # 30mm in points
            page_height = 150 * 2.83  # 150mm in points
            blank_height = 50 * 2.83  # 50mm blank space
            page_size = (page_width, page_height)

            p = canvas.Canvas(buffer, pagesize=portrait(page_size))

            # Calculate total pages including copies
            total_pages = sum(4 if t.product_code.startswith("C") else 1 for t in tags)
            current_page = 0

            for tag in tags:
                copies = 4 if tag.product_code.startswith("C") else 1
                for _ in range(copies):
                    current_page += 1

                    # Generate QR code URL that points to your frontend
                    qr_url = f"https://tracemyleather.netlify.app/tags/{tag.new_tag}"
                    qr_img = self.generate_qr_code(qr_url)

                    qr_buffer = BytesIO()
                    qr_img.save(qr_buffer, format="PNG")
                    qr_buffer.seek(0)
                    qr_image = ImageReader(qr_buffer)

                    # Position content after blank space
                    content_start_y = blank_height
                    qr_x = (page_width - 95) / 2
                    qr_y = content_start_y + 10

                    # Draw page number
                    p.setFont("Helvetica-Bold", 16)
                    p.drawString(qr_x + 33, qr_y + 120, f"{current_page}/{total_pages}")

                    # Draw batch number
                    p.setFont("Helvetica-Bold", 22)
                    p.drawString(qr_x + 20, qr_y + 100, f"{tag.batch_no}")

                    # Draw date
                    p.setFont("Helvetica-Bold", 10)
                    p.drawString(qr_x + 20, qr_y + 88, tag.datetime.strftime('%d-%m-%Y'))

                    # Draw QR code
                    p.drawImage(qr_image, qr_x + 5, qr_y + 2, width=85, height=85)

                    # Draw vertical text (rotated)
                    p.saveState()
                    text_x = qr_x + 25
                    text_y = qr_y - 10
                    p.translate(text_x, text_y)
                    p.rotate(-90)

                    p.setFont("Helvetica-Bold", 24)
                    p.drawString(-7, 20, f"{tag.new_tag}")
                    p.setFont("Helvetica-Bold", 8)
                    p.drawString(-3, 0, "Funded by The SMEP Programme")

                    p.restoreState()

                    # Draw borders
                    p.setStrokeColorRGB(0, 0, 0)
                    p.setLineWidth(1)
                    p.rect(0, 0, page_width, page_height)

                    # Draw cutting lines
                    p.setLineWidth(2)
                    p.line(0, page_height - 1, page_width, page_height - 1)  # Top
                    p.line(0, 1, page_width, 1)  # Bottom

                    p.showPage()

            p.save()
            buffer.seek(0)

            # Return PDF response
            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/pdf',
                headers={
                    'Content-Disposition': 'inline; filename="tags.pdf"'
                }
            )
            return response

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportTagsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        try:
            if start_date_str and end_date_str:
                start_date = parse_date(start_date_str)
                end_date = parse_date(end_date_str)
                tag_entries = TagGeneration.objects.filter(
                    datetime__date__range=(start_date, end_date)
                ).order_by('-datetime')
            else:
                tag_entries = TagGeneration.objects.all().order_by('-datetime')

            # Group tags by confirmation
            from collections import defaultdict
            grouped_data = defaultdict(list)
            for tag in tag_entries:
                grouped_data[tag.confirmation].append(tag)

            response = HttpResponse(content_type='text/csv')
            response[
                'Content-Disposition'] = f'attachment; filename="generated_tags_{start_date_str}_to_{end_date_str}.csv"'

            writer = csv.writer(response)
            writer.writerow([
                'Confirmation ID', 'Old Tag(s)', 'New Tag(s)', 'Batch No', 'Owner Name',
                'Animal Type', 'Total Animals', 'Total Tags', 'Price', 'Amount',
                'DateTime', 'User'
            ])

            for confirm_id, tags in grouped_data.items():
                tag = tags[0]  # take representative for metadata
                old_tags = ", ".join(t.old_tag for t in tags if t.old_tag)
                new_tags = ", ".join(t.new_tag for t in tags)

                writer.writerow([
                    tag.confirmation, old_tags, new_tags, tag.batch_no,
                    tag.owner_name, tag.product_code, tag.total_animals,
                    tag.total_tags, tag.rate, tag.amount,
                    tag.datetime.strftime('%Y-%m-%d %I:%M:%S %p') if tag.datetime else '',
                    tag.user.username if tag.user else ''
                ])

            return response

        except ValueError:
            return Response({"error": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdatePrintCountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, tag_id):
        try:
            tag = TagGeneration.objects.get(new_tag=tag_id)
            tag.print_count += 1
            tag.save()
            return Response({"print_count": tag.print_count})
        except TagGeneration.DoesNotExist:
            return Response({"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def material_sources_chart(request):
    sources = ['Cow', 'Buffalo', 'Sheep', 'Goat']
    data = {
        'labels': sources,
        'datasets': [{
            'label': 'Material Sources',
            'data': [TagGeneration.objects.filter(hide_source=source).count() for source in sources],
            'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
        }]
    }
    return Response(data)


class RoleBasedDashboardAPI(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        profile = request.user.profile
        context = {
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "is_superuser": request.user.is_superuser,
            },
            "profile": {
                "role": profile.role,
                "email_verified": profile.email_verified,
                "business_type": profile.business_type,
                "operation_type": profile.operation_type,
                "animal_types": profile.animal_types,
                "leather_types": profile.leather_types,
                "city": profile.city,
                "location": profile.location,
                "certifications": profile.certifications
            }
        }
        return Response(context)


class HandleActionAPI(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        action_type = request.data.get('type')  # 'trader', 'tannery', 'garment'
        action_field = request.data.get('action')  # 'arrived', 'dispatched'
        search_id = request.data.get('search_id', '').strip()

        if not all([action_type, action_field, search_id]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tag = TagGeneration.objects.get(new_tag=search_id)
            current_time = datetime.now(pytz.timezone('Asia/Karachi'))

            if action_type == 'trader':
                return self._handle_trader_action(tag, action_field, request.user, current_time)
            elif action_type == 'tannery':
                return self._handle_tannery_action(tag, action_field, request.user, current_time, request.data)
            elif action_type == 'garment':
                return self._handle_garment_action(tag, action_field, request.user, current_time, request.data)
            else:
                return Response({"error": "Invalid action type"}, status=status.HTTP_400_BAD_REQUEST)

        except TagGeneration.DoesNotExist:
            return Response({"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_trader_action(self, tag, action_field, user, current_time):
        profile = user.profile
        location = profile.city
        if action_field == 'arrived':
            if tag.trader_arrived:
                return Response({"error": f"Tag {tag.new_tag} already arrived at trader"},
                                status=status.HTTP_400_BAD_REQUEST)

            tag.trader_arrived = current_time
            tag.save()

            TransactionLog.objects.create(
                new_tag=tag,
                user=user,
                action='arrived',
                actor_type='trader',
                timestamp=current_time,
                location=location
            )

            return Response({"message": f"Tag {tag.new_tag} arrived at trader"})

        elif action_field == 'dispatched':
            if not tag.trader_arrived:
                return Response({"error": f"Tag {tag.new_tag} must arrive before dispatch"},
                                status=status.HTTP_400_BAD_REQUEST)
            if tag.trader_dispatched:
                return Response({"error": f"Tag {tag.new_tag} already dispatched from trader"},
                                status=status.HTTP_400_BAD_REQUEST)

            tag.trader_dispatched = current_time
            tag.save()

            TransactionLog.objects.create(
                new_tag=tag,
                user=user,
                action='dispatched',
                actor_type='trader',
                timestamp=current_time,
                location = location
            )

            return Response({"message": f"Tag {tag.new_tag} dispatched from trader"})

        return Response({"error": "Invalid trader action"}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_tannery_action(self, tag, action_field, user, current_time, data):
        profile = user.profile
        location = profile.city
        if action_field == 'arrived':
            if tag.tannery_arrived:
                return Response({"error": f"Tag {tag.new_tag} already arrived at tannery"},
                                status=status.HTTP_400_BAD_REQUEST)

            tannery_stamp_code = data.get('tannery_stamp_code', '').strip()
            hide_source = data.get('hide_source')
            vehicle_number = data.get('vehicle_number')

            if not all([tannery_stamp_code, hide_source]):
                return Response({"error": "Stamp code and hide source are required"},
                                status=status.HTTP_400_BAD_REQUEST)

            tag.tannery_arrived = current_time
            tag.tannery_stamp_code = tannery_stamp_code
            tag.hide_source = hide_source
            tag.vehicle_number = vehicle_number
            tag.save()

            TransactionLog.objects.create(
                new_tag=tag,
                user=user,
                action='arrived',
                actor_type='tannery',
                timestamp=current_time,
                location=location,
            )

            return Response({"message": f"Tag {tag.new_tag} arrived at tannery with stamp {tannery_stamp_code}"})

        elif action_field == 'dispatched':
            tannery_stamp_code = data.get('tannery_stamp_code', '').strip()
            processed_lot_number = data.get('processed_lot_number')
            dispatch_to = data.get('dispatch_to')
            article = data.get('article', '').strip()
            tannage_type = data.get('tannage_type')

            if not all([tannery_stamp_code, processed_lot_number, dispatch_to]):
                return Response({"error": "All dispatch fields are required"}, status=status.HTTP_400_BAD_REQUEST)

            if tag.tannery_stamp_code != tannery_stamp_code:
                return Response({"error": "Stamp code mismatch"}, status=status.HTTP_400_BAD_REQUEST)

            if not tag.tannery_arrived:
                return Response({"error": f"Tag {tag.new_tag} has not arrived at tannery"},
                                status=status.HTTP_400_BAD_REQUEST)
            if tag.tannery_dispatched:
                return Response({"error": f"Tag {tag.new_tag} already dispatched from tannery"},
                                status=status.HTTP_400_BAD_REQUEST)

            tag.tannery_dispatched = current_time
            tag.processed_lot_number = processed_lot_number
            tag.dispatch_to = dispatch_to
            tag.article = article
            tag.tannage_type = tannage_type
            tag.save()

            TransactionLog.objects.create(
                new_tag=tag,
                user=user,
                action='dispatched',
                actor_type='tannery',
                timestamp=current_time,
                location=location,
            )

            return Response({
                "message": f"Dispatched stamp {tannery_stamp_code} ({tag.new_tag}) to {dispatch_to}",
                "lot_number": processed_lot_number
            })

        return Response({"error": "Invalid tannery action"}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_garment_action(self, tag, action_field, user, current_time, data):
        profile = user.profile
        location = profile.city
        if action_field == 'arrived':
            if tag.garment_arrived:
                return Response({"error": f"Tag {tag.new_tag} already arrived at garment"},
                                status=status.HTTP_400_BAD_REQUEST)
            if not tag.tannery_dispatched:
                return Response({"error": f"Tag {tag.new_tag} not dispatched from tannery"},
                                status=status.HTTP_400_BAD_REQUEST)

            tag.garment_arrived = current_time
            tag.save()

            TransactionLog.objects.create(
                new_tag=tag,
                user=user,
                action='arrived',
                actor_type='garment',
                timestamp=current_time,
                location=location
            )

            return Response({"message": f"Tag {tag.new_tag} arrived at garment"})

        elif action_field == 'dispatched':
            if not tag.garment_arrived:
                return Response({"error": f"Tag {tag.new_tag} not arrived at garment"},
                                status=status.HTTP_400_BAD_REQUEST)
            if tag.garment_dispatched:
                return Response({"error": f"Tag {tag.new_tag} already dispatched from garment"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Handle garment product creation and dispatch
            try:
                with transaction.atomic():
                    product_types = data.get('product_types', [])
                    brand = data.get('brand', '')
                    other_product_type = data.get('other_product_type', '').strip()
                    g_date_str = data.get('g_date')
                    g_date = timezone.now() if not g_date_str else timezone.make_aware(
                        datetime.strptime(g_date_str, "%Y-%m-%d %H:%M:%S"))
                    num_pieces = int(data.get('num_pieces', 0))

                    if num_pieces < 1:
                        return Response({"error": "Invalid number of pieces"}, status=status.HTTP_400_BAD_REQUEST)

                    if 'Other' in product_types and not other_product_type:
                        return Response({"error": "Please specify custom product type"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    garment = GarmentProduct.objects.create(
                        user=user,
                        num_pieces=num_pieces,
                        product_types=','.join(product_types),
                        brand=brand,
                        other_product_type=other_product_type,
                        g_date=g_date,
                        time_stamp=current_time,
                    )

                    tag.garment_product = garment
                    tag.garment_dispatched = current_time
                    tag.g_date = garment.g_date
                    tag.product_types = garment.product_types
                    tag.brand = garment.brand
                    tag.other_product_type = garment.other_product_type
                    tag.save()

                    TransactionLog.objects.create(
                        new_tag=tag,
                        user=user,
                        action='dispatched',
                        actor_type='garment',
                        timestamp=current_time,
                        location=location
                    )

                    return Response({
                        "message": f"Created garment product {garment.garment_id}",
                        "garment_id": garment.garment_id
                    })

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid garment action"}, status=status.HTTP_400_BAD_REQUEST)


# In views.py, update the TraceAPI view
class TraceAPI(viewsets.ViewSet):
    permission_classes = []  # Remove authentication requirement

    def create(self, request):
        search_term = request.data.get('search_id', '').strip().upper()
        if not search_term:
            return Response({"error": "Please enter a valid ID"}, status=status.HTTP_400_BAD_REQUEST)

        # Check for garment ID first
        if len(search_term) == 12 and search_term.isalnum():
            try:
                garment = GarmentProduct.objects.prefetch_related(
                    'tags__transaction_logs__user__profile'
                ).get(garment_id=search_term)
                return Response({
                    "type": "garment",
                    "id": garment.garment_id,
                    "data": GarmentProductSerializer(garment).data,
                    "tags": TagGenerationSerializer(
                        garment.tags.all(),
                        many=True
                    ).data
                })
            except GarmentProduct.DoesNotExist:
                pass

        # Check for tag ID or tannery stamp code
        try:
            tag = TagGeneration.objects.prefetch_related(
                'transaction_logs__user__profile'
            ).get(new_tag=search_term)
        except TagGeneration.DoesNotExist:
            try:
                tag = TagGeneration.objects.prefetch_related(
                    'transaction_logs__user__profile'
                ).get(tannery_stamp_code=search_term)
            except TagGeneration.DoesNotExist:
                return Response(
                    {"error": f"No results found for: {search_term}"},
                    status=status.HTTP_404_NOT_FOUND
                )

        response_data = {
            "type": "tag",
            "id": tag.new_tag,
            "data": TagGenerationSerializer(tag).data,
            "transactions": TransactionLogSerializer(
                tag.transaction_logs.all().order_by('timestamp'),
                many=True
            ).data
        }

        if tag.garment_product:
            response_data["garment"] = GarmentProductSerializer(tag.garment_product).data

        return Response(response_data)


class TraderDashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            # Allow superusers OR users with trader role
            if not (request.user.is_superuser or profile.role == 'trader' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            serializer = ProfileSerializer(profile)
            return Response({
                "profile": serializer.data,
                "last_login": request.user.last_login
            })
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)


class TraderTransactionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'trader' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            search_query = request.query_params.get('search', '').strip()

            # Filter transactions
            if request.user.is_superuser:
                transactions = TransactionLog.objects.filter(actor_type='trader')
            else:
                transactions = TransactionLog.objects.filter(user=request.user, actor_type='trader')

            transactions = transactions.select_related('new_tag').order_by('-timestamp')

            if search_query:
                transactions = transactions.filter(
                    Q(new_tag__new_tag__icontains=search_query) |
                    Q(action__icontains=search_query)
                )

            paginator = Paginator(transactions, page_size)
            page_obj = paginator.page(page)

            data = []
            for t in page_obj:
                tag = t.new_tag
                data.append({
                    'id': t.id,
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'tag_id': tag.new_tag if tag else None,
                    'arrival_date': tag.trader_arrived if tag else None,
                    'dispatch_date': tag.trader_dispatched if tag else None,
                    'user': t.user.username if t.user else None,
                })

            return Response({
                'transactions': data,
                'total': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'trader'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            search_id = request.data.get('search_id', '').strip()
            action = request.data.get('action')

            if not search_id:
                return Response({"error": "Please provide a valid ID"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                tag = TagGeneration.objects.get(new_tag=search_id)
                current_time = timezone.now()

                if action == 'arrived':
                    if tag.trader_arrived:
                        return Response({"error": f"Tag {tag.new_tag} already arrived"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    tag.trader_arrived = current_time
                    tag.save()

                    TransactionLog.objects.create(
                        new_tag=tag,
                        user=request.user,
                        action='arrived',
                        actor_type='trader',
                        timestamp=current_time
                    )

                    return Response({"success": f"Tag {tag.new_tag} arrived at trader"})

                elif action == 'dispatched':
                    if not tag.trader_arrived:
                        return Response({"error": f"Tag {tag.new_tag} must arrive before dispatch"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    if tag.trader_dispatched:
                        return Response({"error": f"Tag {tag.new_tag} already dispatched"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    tag.trader_dispatched = current_time
                    tag.save()

                    TransactionLog.objects.create(
                        new_tag=tag,
                        user=request.user,
                        action='dispatched',
                        actor_type='trader',
                        timestamp=current_time
                    )

                    return Response({"success": f"Tag {tag.new_tag} dispatched from trader"})

                else:
                    return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

            except TagGeneration.DoesNotExist:
                return Response({"error": f"No record found for ID: {search_id}"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TanneryDashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            # Allow superusers OR users with tannery role
            if not (request.user.is_superuser or profile.role == 'tannery' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            serializer = ProfileSerializer(profile)
            return Response({
                "profile": serializer.data,
                "last_login": request.user.last_login
            })
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'tannery'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            action = request.data.get('action')
            current_time = timezone.now()

            with transaction.atomic():
                if action == 'arrived':
                    return self._handle_arrival(request, current_time)
                elif action == 'dispatched':
                    return self._handle_dispatch(request, current_time)
                else:
                    return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_arrival(self, request, current_time):
        search_tag = request.data.get('search_id', '').strip()
        tannery_stamp_code = request.data.get('tannery_stamp_code', '').strip()
        hide_source = request.data.get('hide_source')
        vehicle_number = request.data.get('vehicle_number')

        if not all([search_tag, tannery_stamp_code, hide_source]):
            raise ValidationError("Tag ID, Stamp Code, and Hide Source are required")

        if TagGeneration.objects.filter(tannery_stamp_code=tannery_stamp_code).exists():
            raise ValidationError(f"Stamp code {tannery_stamp_code} already in use")

        tag = TagGeneration.objects.get(new_tag=search_tag)

        if tag.tannery_arrived:
            raise ValidationError(
                f"Tag {search_tag} has already arrived at tannery "
                f"(Arrival Time: {tag.tannery_arrived})"
            )

        tag.tannery_arrived = current_time
        tag.tannery_stamp_code = tannery_stamp_code
        tag.hide_source = hide_source
        tag.vehicle_number = vehicle_number
        tag.save()

        TransactionLog.objects.create(
            new_tag=tag,
            user=request.user,
            action='arrived',
            actor_type='tannery',
            timestamp=current_time
        )

        return Response({
            "success": f"Tag {search_tag} arrived with stamp {tannery_stamp_code}",
            "tag": TagGenerationSerializer(tag).data
        })

    def _handle_dispatch(self, request, current_time):
        tannery_stamp_code = request.data.get('tannery_stamp_code', '').strip()
        processed_lot_number = request.data.get('processed_lot_number')
        dispatch_to = request.data.get('dispatch_to')
        article = request.data.get('article', '').strip()  # Add this
        tannage_type = request.data.get('tannage_type')

        if not all([tannery_stamp_code, processed_lot_number, dispatch_to]):
            raise ValidationError("All dispatch fields are required")

        tag = TagGeneration.objects.get(tannery_stamp_code=tannery_stamp_code)

        if tag.tannery_dispatched:
            raise ValidationError(
                f"Stamp code {tannery_stamp_code} was already dispatched "
                f"on {tag.tannery_dispatched.strftime('%Y-%m-%d %H:%M')}"
            )

        if not tag.tannery_arrived:
            raise ValidationError(
                f"Stamp code {tannery_stamp_code} has not arrived at tannery"
            )

        tag.tannery_dispatched = current_time
        tag.processed_lot_number = processed_lot_number
        tag.dispatch_to = dispatch_to
        tag.article = article  # Add this
        tag.tannage_type = tannage_type
        tag.save()

        TransactionLog.objects.create(
            new_tag=tag,
            user=request.user,
            action='dispatched',
            actor_type='tannery',
            timestamp=current_time
        )

        return Response({
            "success": f"Dispatched stamp {tannery_stamp_code} ({tag.new_tag}) to {dispatch_to}",
            "lot_number": processed_lot_number,
            "tag": TagGenerationSerializer(tag).data
        })


class TanneryTransactionsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'tannery' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            search_query = request.query_params.get('search', '').strip()

            # Filter transactions
            if request.user.is_superuser:
                transactions = TransactionLog.objects.filter(actor_type='tannery')
            else:
                transactions = TransactionLog.objects.filter(user=request.user, actor_type='tannery')

            transactions = transactions.select_related('new_tag').order_by('-timestamp')

            if search_query:
                transactions = transactions.filter(
                    Q(new_tag__new_tag__icontains=search_query) |
                    Q(new_tag__tannery_stamp_code__icontains=search_query) |
                    Q(action__icontains=search_query)
                )

            paginator = Paginator(transactions, page_size)
            page_obj = paginator.page(page)

            data = []
            for t in page_obj:
                tag = t.new_tag
                data.append({
                    'id': t.id,
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'tag_id': tag.new_tag if tag else None,
                    'tannery_stamp_code': tag.tannery_stamp_code if tag else None,
                    'arrival_date': tag.tannery_arrived if tag else None,
                    'dispatch_date': tag.tannery_dispatched if tag else None,
                    'vehicle_number': tag.vehicle_number if tag else None,
                    'processed_lot_number': tag.processed_lot_number if tag else None,
                    'dispatch_to': tag.dispatch_to if tag else None,
                    'hide_source': tag.hide_source if tag else None,
                    'user': t.user.username if t.user else None,
                })

            return Response({
                'transactions': data,
                'total': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GarmentDashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            # Allow superusers OR users with garment role
            if not (request.user.is_superuser or profile.role == 'garment' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            serializer = ProfileSerializer(profile)
            return Response({
                "profile": serializer.data,
                "last_login": request.user.last_login
            })
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)


class GarmentTransactionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'garment' or profile.role == 'visitor'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            search_query = request.query_params.get('search', '').strip()

            # Filter transactions
            if request.user.is_superuser:
                transactions = TransactionLog.objects.filter(actor_type='garment')
            else:
                transactions = TransactionLog.objects.filter(user=request.user, actor_type='garment')

            transactions = transactions.select_related('new_tag', 'garment_product').order_by('-timestamp')

            if search_query:
                transactions = transactions.filter(
                    Q(new_tag__new_tag__icontains=search_query) |
                    Q(new_tag__tannery_stamp_code__icontains=search_query) |
                    Q(garment_product__garment_id__icontains=search_query) |
                    Q(action__icontains=search_query)
                )

            paginator = Paginator(transactions, page_size)
            page_obj = paginator.page(page)

            data = []
            for t in page_obj:
                tag = t.new_tag
                data.append({
                    'id': t.id,
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'tag_id': tag.new_tag if tag else None,
                    'tannery_stamp_code': tag.tannery_stamp_code if tag else None,
                    'arrival_date': tag.garment_arrived if tag else None,
                    'dispatch_date': tag.garment_dispatched if tag else None,
                    'garment_id': tag.garment_product.garment_id if tag and tag.garment_product else None,
                    'product_types': tag.product_types if tag else None,
                    'brand': tag.brand if tag else None,
                    'user': t.user.username if t.user else None,
                })

            return Response({
                'transactions': data,
                'total': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == 'garment'):
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            action = request.data.get('action')
            current_time = timezone.now()

            if action == 'arrived':
                return self._handle_arrival(request, current_time)
            elif action == 'dispatched':
                return self._handle_dispatch(request, current_time)
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_arrival(self, request, current_time):
        stamp_code = request.data.get('search_id', '').strip()

        if not stamp_code.isdigit():
            return Response({"error": "Only numbers allowed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                tag = TagGeneration.objects.get(tannery_stamp_code=stamp_code)

                if not tag.tannery_dispatched:
                    return Response(
                        {"error": f"Stamp {stamp_code} not dispatched from tannery"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if tag.garment_arrived:
                    return Response(
                        {"error": f"Stamp {stamp_code} already arrived at {tag.garment_arrived}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                tag.garment_arrived = current_time
                tag.save()

                TransactionLog.objects.create(
                    user=request.user,
                    tannery_stamp_code=stamp_code,
                    new_tag=tag,
                    action='arrived',
                    actor_type='garment',
                    timestamp=current_time
                )

                return Response({"success": f"Received stamp: {stamp_code}"})

        except TagGeneration.DoesNotExist:
            return Response({"error": f"Invalid stamp code: {stamp_code}"}, status=status.HTTP_404_NOT_FOUND)

    def _handle_dispatch(self, request, current_time):
        try:
            with transaction.atomic():
                tag_ids = [t.strip().upper() for t in request.data.get('tag_ids', [])]
                product_types = request.data.get('product_types', [])
                brand = request.data.get('brand', '').strip()
                other_product_type = request.data.get('other_product_type', '').strip()
                g_date_str = request.data.get('g_date')

                # Handle date parsing more flexibly
                try:
                    g_date = timezone.now() if not g_date_str else timezone.make_aware(
                        datetime.strptime(g_date_str, "%Y-%m-%dT%H:%M:%S")  # Match frontend format
                    )
                except ValueError:
                    g_date = timezone.now()

                num_pieces = int(request.data.get('num_pieces', len(tag_ids)))

                # Validate product types
                if 'Other' in product_types and not other_product_type:
                    return Response(
                        {"error": "Please specify the custom product type"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                tags = []
                for tag_id in tag_ids:
                    try:
                        # Search by both tannery_stamp_code and new_tag
                        tag = TagGeneration.objects.get(
                            Q(tannery_stamp_code=tag_id) | Q(new_tag=tag_id)
                        )

                        if not tag.tannery_dispatched:
                            return Response(
                                {"error": f"Tag {tag_id} not dispatched from tannery"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        if not tag.garment_arrived:
                            return Response(
                                {"error": f"Tag {tag_id} not arrived at garment factory"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        if tag.garment_dispatched:
                            return Response(
                                {"error": f"Tag {tag_id} already dispatched"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        tags.append(tag)
                    except TagGeneration.DoesNotExist:
                        return Response(
                            {"error": f"Invalid tag ID: {tag_id}"},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    except TagGeneration.MultipleObjectsReturned:
                        return Response(
                            {"error": f"Multiple tags found for {tag_id}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Create garment product
                garment = GarmentProduct.objects.create(
                    user=request.user,
                    num_pieces=num_pieces,
                    product_types=','.join(product_types),
                    brand=brand,
                    other_product_type=other_product_type,
                    g_date=g_date,
                    time_stamp=current_time
                )

                # Update all tags
                for tag in tags:
                    tag.garment_product = garment
                    tag.garment_dispatched = current_time
                    tag.g_date = g_date
                    tag.product_types = garment.product_types
                    tag.brand = garment.brand
                    tag.other_product_type = garment.other_product_type
                    tag.save()

                    TransactionLog.objects.create(
                        user=request.user,
                        tannery_stamp_code=tag.tannery_stamp_code,
                        new_tag=tag,
                        garment_product=garment,
                        action='dispatched',
                        actor_type='garment',
                        timestamp=current_time
                    )

                return Response({
                    "success": True,
                    "garment_id": garment.garment_id,
                    "message": f"Created garment product {garment.garment_id}"
                })

        except Exception as e:
            logger.error(f"Garment dispatch error: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GarmentProductsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search_query = request.query_params.get('search', '').strip()

        # Base queryset with permission control
        if request.user.is_staff:
            products = GarmentProduct.objects.all()
        else:
            products = GarmentProduct.objects.filter(user=request.user)

        products = products.order_by('-time_stamp')

        # Search logic
        if search_query:
            search_terms = search_query.split()
            query = Q()
            for term in search_terms:
                query &= (
                        Q(garment_id__icontains=term) |
                        Q(brand__icontains=term) |
                        Q(product_types__icontains=term) |
                        Q(tags__new_tag__icontains=term)
                )
            products = products.filter(query).distinct()

        # Pagination
        page = request.query_params.get('page', 1)
        paginator = Paginator(products, 24)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = GarmentProductSerializer(page_obj, many=True)

        return Response({
            "products": serializer.data,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "search_query": search_query,
            "is_admin": request.user.is_staff
        })


class PrintGarmentQRAPI(APIView):
    permission_classes = []  # No authentication required for printing

    def generate_qr_code(self, data):
        """Generates QR code and returns it as PIL Image object."""
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        return img

    def get(self, request, garment_id):
        try:
            # Get garment product
            garment = GarmentProduct.objects.get(garment_id=garment_id)

            # Create PDF buffer
            buffer = BytesIO()

            # Page size (30mm x 150mm) - same as leather tags
            page_width = 30 * 2.83  # 30mm in points
            page_height = 150 * 2.83  # 150mm in points
            blank_height = 50 * 2.83  # 50mm blank space
            page_size = (page_width, page_height)

            p = canvas.Canvas(buffer, pagesize=portrait(page_size))

            # Calculate total pages (1 per garment)
            total_pages = 1
            current_page = 1

            # Generate QR code URL that points to your frontend
            qr_url = f"https://tracemyleather.netlify.app/trace?search={garment.garment_id}"
            qr_img = self.generate_qr_code(qr_url)

            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            qr_image = ImageReader(qr_buffer)

            # Position content after blank space
            content_start_y = blank_height
            qr_x = (page_width - 95) / 2
            qr_y = content_start_y + 10

            # Draw page number
            p.setFont("Helvetica-Bold", 16)
            p.drawString(qr_x + 33, qr_y + 110, f"{current_page}/{total_pages}")

            # Draw brand name
            p.setFont("Helvetica-Bold", 12)
            p.drawString(qr_x + 20, qr_y + 100, f"{garment.brand}")

            # Draw date
            p.setFont("Helvetica-Bold", 10)
            p.drawString(qr_x + 20, qr_y + 88, garment.g_date.strftime('%d-%m-%Y'))

            # Draw QR code
            p.drawImage(qr_image, qr_x + 5, qr_y + 2, width=85, height=85)

            # Draw vertical text (rotated)
            p.saveState()
            text_x = qr_x + 25
            text_y = qr_y - 10
            p.translate(text_x, text_y)
            p.rotate(-90)

            p.setFont("Helvetica-Bold", 16)
            p.drawString(-7, 20, f"{garment.garment_id}")
            p.setFont("Helvetica-Bold", 8)
            p.drawString(-3, 0, "Funded by The SMEP Programme")

            p.restoreState()

            # Draw borders
            p.setStrokeColorRGB(0, 0, 0)
            p.setLineWidth(1)
            p.rect(0, 0, page_width, page_height)

            # Draw cutting lines
            p.setLineWidth(2)
            p.line(0, page_height - 1, page_width, page_height - 1)  # Top
            p.line(0, 1, page_width, 1)  # Bottom

            p.showPage()
            p.save()
            buffer.seek(0)

            # Return PDF response
            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/pdf',
                headers={
                    'Content-Disposition': 'inline; filename="garment_qr.pdf"'
                }
            )
            return response

        except GarmentProduct.DoesNotExist:
            return Response(
                {"error": "Garment product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidateStampAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get('code', '').strip().upper()  # Normalize to uppercase
        response = {'valid': False, 'error': None, 'formatted': None}

        try:
            # First try to find by tannery_stamp_code
            tag = TagGeneration.objects.get(tannery_stamp_code=code)
            response['formatted'] = f"{code} (Tag: {tag.new_tag})"

            # Check all required states
            if not tag.tannery_dispatched:
                response['error'] = "Not dispatched from tannery"
            elif not tag.garment_arrived:
                response['error'] = "Not arrived at garment factory"
            elif tag.garment_dispatched:
                response['error'] = "Already dispatched from garment factory"
            else:
                response['valid'] = True

        except TagGeneration.DoesNotExist:
            # If not found by tannery_stamp_code, try by new_tag
            try:
                tag = TagGeneration.objects.get(new_tag=code)
                response['formatted'] = f"{tag.tannery_stamp_code} (Tag: {code})"

                if not tag.tannery_dispatched:
                    response['error'] = "Not dispatched from tannery"
                elif not tag.garment_arrived:
                    response['error'] = "Not arrived at garment factory"
                elif tag.garment_dispatched:
                    response['error'] = "Already dispatched from garment factory"
                else:
                    response['valid'] = True

            except TagGeneration.DoesNotExist:
                response['error'] = "Invalid stamp code or tag ID"

        return Response(response)


class UserTransactionsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            search_query = request.query_params.get('search', '').strip()

            # Get user's profile to determine role
            profile = request.user.profile

            # Base queryset - superusers see all, regular users see only their transactions
            if request.user.is_superuser:
                # Superusers see all transactions of the specific actor type
                transactions = TransactionLog.objects.all()
            else:
                # Regular users see only their own transactions of their role type
                transactions = TransactionLog.objects.filter(user=request.user)

            # Apply role-specific filtering
            if profile.role == 'trader':
                transactions = transactions.filter(actor_type='trader')
            elif profile.role == 'tannery':
                transactions = transactions.filter(actor_type='tannery')
            elif profile.role == 'garment':
                transactions = transactions.filter(actor_type='garment')
            # Add other roles as needed

            transactions = transactions.select_related('new_tag', 'garment_product').order_by('-timestamp')

            # Apply search filter if provided
            if search_query:
                transactions = transactions.filter(
                    Q(new_tag__new_tag__icontains=search_query) |
                    Q(new_tag__tannery_stamp_code__icontains=search_query) |
                    Q(garment_product__garment_id__icontains=search_query) |
                    Q(action__icontains=search_query)
                )

            paginator = Paginator(transactions, page_size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            # Format data for response
            data = []
            for t in page_obj:
                tag = t.new_tag
                data.append({
                    'id': t.id,
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'actor_type': t.actor_type,
                    'user': t.user.username if t.user else None,
                    'tag_id': tag.new_tag if tag else None,
                    'tannery_stamp_code': tag.tannery_stamp_code if tag else None,
                    # Use appropriate dates based on actor type
                    'arrival_date': (
                        tag.trader_arrived if t.actor_type == 'trader' else
                        tag.tannery_arrived if t.actor_type == 'tannery' else
                        tag.garment_arrived if t.actor_type == 'garment' else None
                    ),
                    'dispatch_date': (
                        tag.trader_dispatched if t.actor_type == 'trader' else
                        tag.tannery_dispatched if t.actor_type == 'tannery' else
                        tag.garment_dispatched if t.actor_type == 'garment' else None
                    ),
                    'vehicle_number': tag.vehicle_number if tag else None,
                    'processed_lot_number': tag.processed_lot_number if tag else None,
                    'dispatch_to': tag.dispatch_to if tag else None,
                    'hide_source': tag.hide_source if tag else None,
                    'garment_id': tag.garment_product.garment_id if tag and tag.garment_product else None,
                    'product_types': tag.product_types if tag else None,
                    'brand': tag.brand if tag else None,
                })

            return Response({
                'transactions': data,
                'total': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'user_role': profile.role,
                'is_superuser': request.user.is_superuser
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
