# views.py
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
import qrcode
import io
import base64
import logging
from welc.models import TagGeneration
from .forms import EditQRForm, EmailQRForm
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)


def generate_qr_pil(data):
    """Generate QR code as PIL image with error handling"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img, None
    except Exception as e:
        logger.error(f"QR Generation Error: {str(e)}")
        return None, str(e)


def generate_qr_code(data):
    """Generate QR code as base64 with error handling"""
    img, error = generate_qr_pil(data)
    if error:
        return None, error
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode(), None


@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def view_qr_codes(request):
    if not (request.user.is_superuser or request.user.profile.role == 'slaughterhouse'):
        return HttpResponse("Unauthorized access", status=403)

    try:
        base_query = TagGeneration.objects.all().order_by('-datetime') if request.user.is_superuser \
            else TagGeneration.objects.filter(user=request.user).order_by('-datetime')

        search_query = request.GET.get('search', '').strip().lower()
        if search_query:
            base_query = base_query.filter(
                Q(owner_name__icontains=search_query) |
                Q(batch_no__icontains=search_query) |
                Q(new_tag__icontains=search_query)
            )

        paginator = Paginator(base_query.select_related('user'), 9)
        page_number = request.GET.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        qr_code_list = []
        for qr_code in page_obj:
            qr_url = request.build_absolute_uri(reverse('display_data', args=[qr_code.new_tag]))
            qr_image, error = generate_qr_code(qr_url)

            if error:
                messages.error(request, f"Failed to generate QR code for {qr_code.new_tag}")
                continue

            qr_code_list.append({
                "data": qr_code,
                "type": "manual",
                "qr_image": qr_image,
            })

        return render(request, 'view_qr_codes.html', {
            'qr_codes': qr_code_list,
            'search_query': search_query,
            'page_obj': page_obj,
        })

    except Exception as e:
        logger.error(f"View QR Codes Error: {str(e)}", exc_info=True)
        messages.error(request, "Failed to load QR codes due to a server error.")
        return redirect('home')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def edit_qr_code(request, new_tag):
    try:
        if request.user.is_superuser:
            qr_entry = get_object_or_404(TagGeneration, new_tag=new_tag)
        else:
            qr_entry = get_object_or_404(TagGeneration, new_tag=new_tag, user=request.user)

        form = EditQRForm(instance=qr_entry)
        email_form = EmailQRForm()

        if request.method == 'POST':
            if 'save_changes' in request.POST:
                form = EditQRForm(request.POST, instance=qr_entry)
                if form.is_valid():
                    form.save()
                    messages.success(request, f"Successfully updated {qr_entry.owner_name}'s QR code!")
                    return redirect('view_qr_codes')
                else:
                    messages.error(request, "Please correct the errors below.")

            elif 'send_email' in request.POST:
                email_form = EmailQRForm(request.POST)
                if email_form.is_valid():
                    email = email_form.cleaned_data['email']
                    qr_url = request.build_absolute_uri(reverse('display_data', args=[qr_entry.new_tag]))
                    qr_image, error = generate_qr_code(qr_url)

                    if error:
                        messages.error(request, "Failed to generate QR code for email")
                        logger.error(f"Email QR Generation Failed: {error}")
                        return render(request, 'edit_qr_code.html', {
                            'form': form,
                            'email_form': email_form,
                            'qr_entry': qr_entry
                        })

                    try:
                        email_msg = EmailMessage(
                            subject=f"QR Code for {qr_entry.owner_name}",
                            body=f"Attached QR code details:\n\n"
                                 f"Owner: {qr_entry.owner_name}\n"
                                 f"Tag ID: {qr_entry.new_tag}\n"
                                 f"Batch No: {qr_entry.batch_no}",
                            from_email=settings.EMAIL_HOST_USER,
                            to=[email],
                        )
                        email_msg.attach(
                            f'qr_code_{qr_entry.new_tag}.png',
                            base64.b64decode(qr_image),
                            'image/png'
                        )
                        email_msg.send(fail_silently=False)
                        messages.success(request, f"QR code sent to {email}")
                    except Exception as e:
                        logger.error(f"Email Send Failed: {str(e)}")
                        messages.error(request, "Failed to send email. Please check the email address.")
                    return redirect('view_qr_codes')
                else:
                    messages.error(request, "Invalid email address format.")

        return render(request, 'edit_qr_code.html', {
            'form': form,
            'email_form': email_form,
            'qr_entry': qr_entry
        })

    except TagGeneration.DoesNotExist:
        logger.warning(f"QR Code Not Found: {new_tag}")
        messages.error(request, "The requested QR code could not be found.")
        return redirect('view_qr_codes')
    except Exception as e:
        logger.error(f"Edit QR Error ({new_tag}): {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('view_qr_codes')


@login_required
def print_single_tag(request, new_tag):
    try:
        if request.user.is_superuser:
            tag = get_object_or_404(TagGeneration, new_tag=new_tag)
        else:
            tag = get_object_or_404(TagGeneration, new_tag=new_tag, user=request.user)

        buffer = io.BytesIO()
        page_width = 30 * 2.83  # 30mm
        page_height = 150 * 2.83  # 150mm
        page_size = (page_width, page_height)

        p = canvas.Canvas(buffer, pagesize=portrait(page_size))
        copies = 4 if tag.product_code.startswith("C") else 1

        for current_page in range(1, copies + 1):
            qr_img, error = generate_qr_pil(
                request.build_absolute_uri(reverse('display_data', args=[tag.new_tag]))
            )
            if error:
                messages.error(request, "Failed to generate printable QR code")
                return redirect('view_qr_codes')

            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            qr_image = ImageReader(qr_buffer)

            # Positioning
            qr_x = (page_width - 95) / 2
            qr_y = (50 * 2.83) + 10  # Start after 50mm blank space

            # Batch Number
            p.setFont("Helvetica-Bold", 22)
            p.drawString(qr_x + 20, qr_y + 100, tag.batch_no)

            # QR Code
            p.drawImage(qr_image, qr_x, qr_y + 3, width=95, height=95)

            # Page Number
            p.setFont("Helvetica-Bold", 16)
            p.drawString(qr_x + 33, qr_y + 120, f"{current_page}/{copies}")

            # Vertical Text
            p.saveState()
            p.translate(qr_x + 25, qr_y - 10)
            p.rotate(-90)
            p.setFont("Helvetica-Bold", 28)
            p.drawString(-20, 20, tag.new_tag)
            p.setFont("Helvetica-Bold", 8)
            p.drawString(-10, 0, "Funded by The SMEP Programme")
            p.restoreState()

            # Borders and lines
            p.setStrokeColorRGB(0, 0, 0)
            p.setLineWidth(1)
            p.rect(0, 0, page_width, page_height)
            p.setLineWidth(2)
            p.line(0, page_height - 1, page_width, page_height - 1)
            p.line(0, 1, page_width, 1)

            p.showPage()

        p.save()
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        response['Content-Disposition'] = f'inline; filename="{tag.new_tag}.pdf"'
        return response

    except Exception as e:
        logger.error(f"Print Error ({new_tag}): {str(e)}", exc_info=True)
        messages.error(request, "Failed to generate PDF. Please try again.")
        return redirect('view_qr_codes')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def delete_qr_code(request, new_tag):
    try:
        if request.user.is_superuser:
            qr_entry = get_object_or_404(TagGeneration, new_tag=new_tag)
        else:
            qr_entry = get_object_or_404(TagGeneration, new_tag=new_tag, user=request.user)

        if request.method == "POST":
            owner_name = qr_entry.owner_name
            qr_entry.delete()
            messages.success(request, f"Successfully deleted QR code for {owner_name}")
            return redirect('view_qr_codes')

        messages.error(request, "Invalid deletion request")
        return redirect('view_qr_codes')

    except TagGeneration.DoesNotExist:
        logger.warning(f"Delete Failed - QR Not Found: {new_tag}")
        messages.error(request, "QR code not found in system")
        return redirect('view_qr_codes')
    except Exception as e:
        logger.error(f"Delete Error ({new_tag}): {str(e)}", exc_info=True)
        messages.error(request, "Failed to delete QR code. Please try again.")
        return redirect('view_qr_codes')