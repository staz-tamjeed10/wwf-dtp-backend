from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    contact_no = forms.CharField(required=False, label="Contact Number", max_length=15)
    ROLE_CHOICES = [
        ('slaughterhouse', 'Slaughterhouse'),
        ('trader', 'Trader'),
        ('tannery', 'Tannery'),
        ('garment', 'Garment'),
        ('visitor', 'Visitor'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select)
    brand = forms.CharField(required=False, label="Brand")  # Changed to CharField
    business_type = forms.CharField(required=False, label="Business Type")
    LEATHER_CHOICES = [
        ('Full grain', 'Full grain'),
        ('Lining', 'Lining'),
        ('Patent', 'Patent'),
        ('Printed', 'Printed'),
        ('PU coated', 'PU coated'),
        ('Skins', 'Skins'),
        ('Sole', 'Sole'),
        ('Split', 'Split'),
        ('Suede', 'Suede'),
        ('Top Grain Split', 'Top Grain Split'),
        ('Wool-on', 'Wool-on'),
        ('Flesh/Drop Splits', 'Flesh/Drop Splits'),
    ]
    leather_types = forms.MultipleChoiceField(
        choices=LEATHER_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Leather Types"
    )

    ANIMAL_CHOICES = [
        ('Cow', 'Cow'),
        ('Buffalo', 'Buffalo'),
        ('Sheep', 'Sheep'),
        ('Goat', 'Goat'),
        ('Camel', 'Camel'),
    ]
    animal_types = forms.MultipleChoiceField(
        choices=ANIMAL_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Animal Types"
    )

    city = forms.CharField(required=False, label="City")
    location = forms.CharField(required=False, label="Address")
    operation_type = forms.CharField(required=False, label="Operation Type")

    CERTIFICATION_CHOICES = [
        ('ISO 14001', 'ISO 14001'),
        ('ISO 9001', 'ISO 9001'),
        ('ISO 50001', 'ISO 50001'),
        ('LWG', 'LWG'),
        ('OEKO-TEX', 'OEKO-TEX'),
        ('ZDHC', 'ZDHC'),
        ('CSCB', 'CSCB'),
        ('SLF', 'SLF'),
        ('IVN Naturleader', 'IVN Naturleader'),
        ('Other', 'Other'),  # Add "Other" option
    ]
    custom_certification = forms.CharField(
        required=False,
        label="Specify Other Certification",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your custom certification'})
    )
    certifications = forms.MultipleChoiceField(
        choices=CERTIFICATION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['username'].help_text = None

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        if role == 'visitor':
            # Skip validation for optional fields
            return cleaned_data

        brand = cleaned_data.get('brand')

        # Handle custom certification
        certifications = cleaned_data.get('certifications', [])
        custom_cert = cleaned_data.get('custom_certification', '').strip()

        if 'Other' in certifications:
            if not custom_cert:
                self.add_error('custom_certification', 'Please specify your custom certification')
            else:
                certifications.remove('Other')
                certifications.append(custom_cert)
        elif custom_cert:  # If custom cert provided without selecting Other
            self.add_error('custom_certification', 'You must select "Other" to specify a custom certification')

        cleaned_data['certifications'] = certifications

        # Handle custom brand input
        if role in ['slaughterhouse', 'trader', 'tannery', 'garment']:
            if brand == 'Other':
                custom_brand = self.data.get('custom_brand', '').strip()
                if not custom_brand:
                    self.add_error('custom_brand', 'Please enter your brand name.')
                else:
                    cleaned_data['brand'] = custom_brand  # Use custom value
            elif not brand:
                self.add_error('brand', 'Brand selection is required for Slaughterhouse role.')

        return cleaned_data

    def clean_certifications(self):
        certifications = self.cleaned_data.get('certifications', [])
        role = self.cleaned_data.get('role')

        if role in ['slaughterhouse', 'tannery', 'garment'] and not certifications:
            raise forms.ValidationError('Certifications are required for this role.')

        return certifications  # Return the list of certifications

    def clean_contact_no(self):
        contact_no = self.cleaned_data.get('contact_no')
        if contact_no and not contact_no.isdigit():
            raise forms.ValidationError("Contact number must contain only digits.")
        return contact_no

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_city(self):
        city = self.cleaned_data.get('city')
        if city == "Other":
            # Get custom city from POST data
            custom_city = self.data.get('custom_city', '').strip()
            if not custom_city:
                raise forms.ValidationError("Please enter your city name.")
            return custom_city  # Return custom value instead of "Other"
        return city


class UserLoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']  # Removed email from fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''  # Remove default help text


class ProfileUpdateForm(forms.ModelForm):
    ROLE_CHOICES = (
        ('tannery', 'Tannery'),
        ('slaughterhouse', 'Slaughterhouse'),
        ('garment', 'Garment'),
        ('admin', 'Admin')
    )

    CERTIFICATION_CHOICES = (
        ('ISO 14001', 'ISO 14001'),
        ('ISO 9001', 'ISO 9001'),
        ('ISO 50001', 'ISO 50001'),
        ('LWG', 'LWG'),
        ('OEKO-TEX', 'OEKO-TEX'),
        ('ZDHC', 'ZDHC'),
        ('CSCB', 'CSCB'),
        ('SLF', 'SLF'),
        ('IVN Naturleader', 'IVN Naturleader'),
        ('Other', 'Other'),
    )

    LEATHER_CHOICES = [
        ('Full grain', 'Full grain'),
        ('Lining', 'Lining'),
        ('Patent', 'Patent'),
        ('Printed', 'Printed'),
        ('PU coated', 'PU coated'),
        ('Skins', 'Skins'),
        ('Sole', 'Sole'),
        ('Split', 'Split'),
        ('Suede', 'Suede'),
        ('Top Grain Split', 'Top Grain Split'),
        ('Wool-on', 'Wool-on'),
        ('Flesh/Drop Splits', 'Flesh/Drop Splits'),
    ]

    OPERATION_CHOICES = [
        ('Unknown', 'Unknown'),
        ('Raw', 'Raw'),
        ('Raw to Wet', 'Raw to Wet'),
        ('Wet to Finish', 'Wet to Finish'),
        ('Raw to Finish', 'Raw to Finish'),
    ]

    ANIMAL_CHOICES = [
        ('Cow', 'Cow'),
        ('Buffalo', 'Buffalo'),
        ('Sheep', 'Sheep'),
        ('Goat', 'Goat'),
        ('Camel', 'Camel'),
    ]

    contact_no = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter contact number or email'}),
        label="Contact Information"
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'disabled': 'disabled'}),
        required=False
    )

    business_type = forms.CharField(required=False, label="Business Type")
    leather_types = forms.MultipleChoiceField(
        choices=LEATHER_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Leather Types"
    )

    animal_types = forms.MultipleChoiceField(
        choices=ANIMAL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Animal Types"
    )

    operation_type = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        widget=forms.Select,
        required=False,
        label="Operation Type"
    )

    custom_certification = forms.CharField(
        required=False,
        label="Specify Other Certification",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your custom certification'})
    )
    certifications = forms.MultipleChoiceField(
        choices=CERTIFICATION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Profile
        fields = [
            'contact_no', 'role', 'business_type', 'leather_types', 'animal_types',
            'city', 'brand', 'location', 'operation_type', 'certifications'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = self.instance.role

        # Set initial values for leather_types and animal_types as lists
        if self.instance.leather_types:
            self.initial['leather_types'] = self.instance.leather_types.split(', ')

        if self.instance.animal_types:
            self.initial['animal_types'] = self.instance.animal_types.split(', ')

        # City configuration
        self.fields['city'] = forms.ChoiceField(
            choices=[
                ('Unknown', 'Unknown'),
                ('Lahore', 'Lahore'),
                ('Islamabad', 'Islamabad'),
                ('Karachi', 'Karachi'),
                ('Sialkot', 'Sialkot'),
                ('Multan', 'Multan'),
                ('Other', 'Other')
            ],
            required=True,
            initial=self._get_initial_city()
        )

        self.fields['custom_city'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={'placeholder': 'Enter your city'}),
            initial=self._get_custom_city()
        )

        # Brand configuration based on role
        role = self.instance.role.lower() if self.instance.role else None
        # Define brand choices and store predefined brands
        self.brand_choices_map = {
            'slaughterhouse': [('PAMCO', 'PAMCO'), ('Other', 'Other')],
            'trader': [('ABC_Trader', 'ABC_Trader'), ('Other', 'Other')],
            'tannery': [('LeatherField_Tannery', 'LeatherField_Tannery'), ('Other', 'Other')],
            'garment': [('LeatherField_Garment', 'LeatherField_Garment'), ('Other', 'Other')]
        }

        # Store role-specific predefined brands
        self.predefined_brands = []
        if role in self.brand_choices_map:
            self.predefined_brands = [choice[0] for choice in self.brand_choices_map[role] if choice[0] != 'Other']

        # Brand field configuration
        if role in self.brand_choices_map:
            self.fields['brand'] = forms.ChoiceField(
                choices=self.brand_choices_map[role],
                required=True,
                initial=self._get_initial_brand(),
                label="Brand"
            )
            self.fields['custom_brand'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Enter brand name'}),
                initial=self._get_custom_brand()
            )
        else:
            self.fields['brand'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Enter brand name'}),
                label="Brand"
            )

        # Initialize certifications
        if self.instance.certifications:
            self.initial['certifications'] = self.instance.certifications.split(', ')

    def _get_initial_city(self):
        predefined = ['Lahore', 'Islamabad', 'Karachi', 'Sialkot', 'Multan']
        return 'Other' if self.instance.city not in predefined else self.instance.city

    def _get_custom_city(self):
        predefined = ['Lahore', 'Islamabad', 'Karachi', 'Sialkot', 'Multan', 'Unknown']
        return self.instance.city if self.instance.city not in predefined else ''

    def _get_initial_brand(self):
        return self.instance.brand if self.instance.brand in self.predefined_brands else 'Other'

    def _get_custom_brand(self):
        return self.instance.brand if self.instance.brand not in self.predefined_brands + ['Other'] else ''

    def clean(self):
        cleaned_data = super().clean()
        contact_no = cleaned_data.get('contact_no')
        if not contact_no:
            self.add_error('contact_no', 'Contact information is required')
        cleaned_data['role'] = self.instance.role
        # Handle custom certification
        certifications = cleaned_data.get('certifications', [])
        custom_cert = cleaned_data.get('custom_certification', '').strip()

        if 'Other' in certifications:
            if not custom_cert:
                self.add_error('custom_certification', 'Please specify your custom certification')
            else:
                certifications.remove('Other')
                certifications.append(custom_cert)
        elif custom_cert:  # If custom cert provided without selecting Other
            self.add_error('custom_certification', 'You must select "Other" to specify a custom certification')

        cleaned_data['certifications'] = certifications
        # City validation
        city = cleaned_data.get('city')
        custom_city = cleaned_data.get('custom_city', '').strip()
        if city == "Other":
            if not custom_city:
                self.add_error('custom_city', 'Please enter your city')
            else:
                cleaned_data['city'] = custom_city

        # Brand validation for all roles
        brand = cleaned_data.get('brand')
        custom_brand = cleaned_data.get('custom_brand', '').strip()

        if brand == 'Other':
            if not custom_brand:
                self.add_error('custom_brand', 'Brand name is required')
            else:
                cleaned_data['brand'] = custom_brand
        elif not brand and self.instance.role in ['slaughterhouse', 'trader', 'tannery', 'garment']:
            self.add_error('brand', 'Brand is required for this role')

        return cleaned_data

    def clean_certifications(self):
        certifications = self.cleaned_data.get('certifications', [])
        role = self.instance.role.lower() if self.instance.role else None

        if role in ['slaughterhouse', 'tannery', 'garment'] and not certifications:
            raise forms.ValidationError('Certifications are required for this role')

        return certifications

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.certifications = ', '.join(self.cleaned_data.get('certifications', []))
        profile.leather_types = ', '.join(self.cleaned_data.get('leather_types', []))
        profile.animal_types = ', '.join(self.cleaned_data.get('animal_types', []))

        # Handle custom city
        if self.cleaned_data.get('city') == 'Other':
            profile.city = self.cleaned_data.get('custom_city', '')

        if commit:
            profile.save()
        return profile


class PasswordUpdateForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_new_password1(self):
        new_password = self.cleaned_data.get('new_password1')
        if len(new_password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return new_password


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Email', max_length=254)


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="New password",
                                    widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label="Confirm new password",
                                    widget=forms.PasswordInput(attrs={'class': 'form-control'}))

