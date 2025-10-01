from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    registered_since = models.DateField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    token_created_at = models.DateTimeField(null=True, blank=True)
    contact_no = models.CharField(max_length=15, null=True, blank=True)
    role = models.CharField(max_length=20,blank=True, null=True, choices=[('slaughterhouse', 'Slaughterhouse'),
                                                    ('trader', 'Trader'),
                                                    ('tannery', 'Tannery'),
                                                    ('garment', 'Garment'),
                                                    ('visitor', 'Visitor'),
                                                    ('admin', 'Admin'),])
    # New fields
    brand = models.CharField(max_length=100, null=True, blank=True, default="Unknown")
    business_type = models.CharField(max_length=100, null=True, blank=True, default="Unknown")

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

    leather_types = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated leather types")
    ANIMAL_CHOICES = [
        ('Cow', 'Cow'),
        ('Buffalo', 'Buffalo'),
        ('Sheep', 'Sheep'),
        ('Goat', 'Goat'),
        ('Camel', 'Camel'),
    ]
    animal_types = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated animal types")
    city = models.CharField(max_length=100, null=True, blank=True, default="Unknown")
    location = models.CharField(max_length=200, null=True, blank=True, default="Unknown")
    operation_type = models.CharField(max_length=100, null=True, blank=True, default="Unknown")
    certifications = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated list of certifications")  # Allow blank
    time_stamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_profile')
        ]

    def __str__(self):
        return self.user.username

    # Add this method to your Profile model
    def get_leather_types_list(self):
        return [lt.strip() for lt in self.leather_types.split(',')] if self.leather_types else []

    def get_animal_types_list(self):
        return [at.strip() for at in self.animal_types.split(',')] if self.animal_types else []

    def get_certifications_list(self):
        return [cert.strip() for cert in self.certifications.split(',')] if self.certifications else []