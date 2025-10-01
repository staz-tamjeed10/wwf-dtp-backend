from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
class Tannery(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    contact = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name


class Hd(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('Jacket', 'Jacket'),
        ('Gloves', 'Gloves'),
        ('Skirt', 'Skirt'),
        ('Pant', 'Pant'),
        ('Shoes', 'Shoes'),
        ('Wallet', 'Wallet'),
        ('Bag', 'Bag'),
        ('Belt', 'Belt'),
        ('Other', 'Other'),
    ]

    g_date = models.DateTimeField(null=True, blank=True)  # Remove default=timezone.now
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    animal_id = models.CharField(max_length=6, unique=True, null=True, blank=True)
    tag_id = models.CharField(max_length=50, null=True, blank=True)
    owner = models.CharField(max_length=100, null=True, blank=True)
    vehicle_number = models.CharField(max_length=50, null=True, blank=True)  # Vehicle Number Field
    # trader_name = models.CharField(max_length=100, null=True, blank=True)
    processed_lot_number = models.CharField(max_length=100, null=True, blank=True)
    Supplier_id = models.CharField(max_length=50, null=True, blank=True)
    animal_type = models.CharField(max_length=50, null=True, blank=True)
    slaughter_date = models.DateField(null=True, blank=True)
    leather_type = models.CharField(max_length=100, null=True, blank=True)
    origin = models.CharField(max_length=100, null=True, blank=True)
    dispatch_to = models.CharField(max_length=255, null=True, blank=True)
    hide_source = models.CharField(
        max_length=20,
        choices=[('Buffalo', 'Buffalo'), ('Cow', 'Cow'), ('Sheep', 'Sheep'), ('Goat', 'Goat')],
        null=True, blank=True
    )
    tannery_stamp_code = models.CharField(max_length=50, null=True, blank=True)
    product_types = models.CharField(max_length=200, blank=True, null=True)
    other_product_type = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    # traders = models.ManyToManyField(User, related_name="trader_records", blank=True)
    # tannery = models.ForeignKey(Tannery, on_delete=models.SET_NULL, null=True, blank=True, related_name='hides')
    trader_arrived = models.DateTimeField(null=True, blank=True)
    trader_dispatched = models.DateTimeField(null=True, blank=True)
    tannery_arrived = models.DateTimeField(null=True, blank=True)
    tannery_dispatched = models.DateTimeField(null=True, blank=True)
    garment_arrived = models.DateTimeField(null=True, blank=True)
    garment_dispatched = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tag_data'

    def __str__(self):
        return f"HD Record: {self.animal_id} ({self.hide_source})"

    def clean(self):
        # Check for Other product type
        if 'Other' in self.get_product_types_list() and not self.other_product_type:
            raise ValidationError("Please specify 'Other' product type")

        # Check process date only if it exists
        if self.g_date and self.g_date > timezone.now():
            raise ValidationError("Process date cannot be in the future")

    def save(self, *args, **kwargs):
        if not self.animal_id:
            self.animal_id = self.generate_unique_animal_id()
        self.leather_type = self.get_leather_type()
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_unique_animal_id(self):
        while True:
            animal_id = get_random_string(6, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            if not Hd.objects.filter(animal_id=animal_id).exists():
                return animal_id

    def get_leather_type(self):
        if self.animal_type in ['Cow', 'Buffalo', 'Camel', 'Beef']:
            return 'Hide'
        elif self.animal_type in ['Sheep', 'Goat', 'Mutton']:
            return 'Skin'
        return None

    def get_product_types_list(self):
        return self.product_types.split(',') if self.product_types else []


class MemberAccountType(models.Model):
    type = models.CharField(max_length=255)

    class Meta:
        db_table = "member_account_types"


class OffalCollector(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "offal_collectors"


class Member(models.Model):
    old_batch_no = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    expiry_days = models.IntegerField()
    account_type = models.ForeignKey(MemberAccountType, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "members"


class CashEntry(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    offal_collector = models.ForeignKey(OffalCollector, on_delete=models.SET_NULL, null=True)
    command = models.CharField(max_length=255, null=True, blank=True)
    total_animals = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "cash_entries"


class Confirmation(models.Model):
    cash_entry = models.ForeignKey(CashEntry, on_delete=models.CASCADE)
    datetime = models.DateTimeField(default=timezone.now)
    prints_counter = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "confirmations"


class Tag(models.Model):
    tag = models.CharField(max_length=255)
    day_counter = models.CharField(max_length=255)
    datetime = models.DateTimeField(default=timezone.now)
    confirmation = models.ForeignKey(Confirmation, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "tags"


class GarmentProduct(models.Model):
    garment_id = models.CharField(max_length=12, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    num_pieces = models.PositiveIntegerField()
    dispatch_date = models.DateTimeField(null=True, blank=True)
    product_types = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    other_product_type = models.CharField(max_length=100, blank=True, null=True)
    time_stamp = models.DateTimeField(null=True, blank=True)
    g_date = models.DateTimeField(null=True, blank=True,
        help_text="User-specified process date/time",
        verbose_name="Process Date"
    )

    def save(self, *args, **kwargs):
        if not self.garment_id:
            self.garment_id = get_random_string(12, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')

        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.pk:
                self.tags.update(
                    garment_dispatched=timezone.now(),
                    dispatch_to="Garment Factory",
                    product_types=self.product_types,
                    brand=self.brand,
                    other_product_type=self.other_product_type,
                    g_date=self.g_date
                )

    def clean(self):
        conflicts = self.tags.filter(garment_products__isnull=False).exclude(garment_products=self)
        if conflicts.exists():
            conflict_tags = conflicts.values_list('new_tag', flat=True)
            raise ValidationError(f"Tags already used in other garments: {', '.join(conflict_tags)}")
        if 'Other' in self.get_product_types_list() and not self.other_product_type:
            raise ValidationError("Please specify 'Other' product type")

    def get_product_types_list(self):
        return self.product_types.split(',') if self.product_types else []

    def __str__(self):
        return f"Garment-{self.garment_id}"


class TagGeneration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Keep this one
    new_tag = models.CharField(max_length=50, primary_key=True)
    old_tag = models.CharField(max_length=50, null=True, blank=True)
    confirmation = models.CharField(max_length=50, null=True, blank=True)
    batch_no = models.CharField(max_length=50)
    total_animals = models.IntegerField()
    command = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    owner_name = models.CharField(max_length=255)
    expiry_days = models.IntegerField()
    account_type = models.CharField(max_length=50)
    offal_collector = models.CharField(max_length=255, blank=True, null=True)
    datetime = models.DateTimeField(default=timezone.now)
    product_code = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_tags = models.IntegerField()
    total_prints = models.IntegerField()
    print_count = models.IntegerField(default=0)

    hide_source = models.CharField(
        max_length=20,
        choices=[('Buffalo', 'Buffalo'), ('Cow', 'Cow'), ('Sheep', 'Sheep'), ('Goat', 'Goat')],
        null=True, blank=True
    )
    tannery_stamp_code = models.CharField(max_length=50, null=True, blank=True)
    vehicle_number = models.CharField(max_length=50, null=True, blank=True)
    trader_name = models.CharField(max_length=100, null=True, blank=True)
    processed_lot_number = models.CharField(max_length=100, null=True, blank=True)
    dispatch_to = models.CharField(max_length=255, null=True, blank=True)

    PRODUCT_TYPE_CHOICES = [
        ('Jacket', 'Jacket'),
        ('Gloves', 'Gloves'),
        ('Skirt', 'Skirt'),
        ('Pant', 'Pant'),
        ('Shoes', 'Shoes'),
        ('Wallet', 'Wallet'),
        ('Bag', 'Bag'),
        ('Belt', 'Belt'),
        ('Other', 'Other'),
    ]
    product_types = models.CharField(max_length=200, blank=True, null=True, default='')
    brand = models.CharField(max_length=100, blank=True, null=True)
    other_product_type = models.CharField(max_length=100, blank=True, null=True)
    g_date = models.DateTimeField(null=True, blank=True,
        help_text="Process date from garment product"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    garment_product = models.ForeignKey(
        GarmentProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tags'
    )
    trader_arrived = models.DateTimeField(null=True, blank=True)
    trader_dispatched = models.DateTimeField(null=True, blank=True)
    tannery_arrived = models.DateTimeField(null=True, blank=True)
    tannery_dispatched = models.DateTimeField(null=True, blank=True)
    garment_arrived = models.DateTimeField(null=True, blank=True)
    garment_dispatched = models.DateTimeField(null=True, blank=True)
    time_stamp = models.DateTimeField(null=True, blank=True)
    traders = models.ManyToManyField(User, related_name="trader_records", blank=True)
    tannery = models.ForeignKey(Tannery, on_delete=models.SET_NULL, null=True, blank=True, related_name='hides')
    TANNAGE_TYPE_CHOICES = [
        ('Chrome', 'Chrome'),
        ('Chrome-free', 'Chrome-free'),
        ('Vegetable', 'Vegetable'),
    ]

    article = models.CharField(max_length=100, blank=True, null=True)
    tannage_type = models.CharField(
        max_length=20,
        choices=TANNAGE_TYPE_CHOICES,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Tag: {self.new_tag} | Owner: {self.owner_name} | Status: {self.current_status}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['new_tag', 'garment_product'],
                condition=Q(garment_product__isnull=False),
                name='unique_tag_garment'
            )
        ]

    @property
    def current_status(self):
        if self.garment_dispatched:
            return "Dispatched from Garment"
        if self.garment_arrived:
            return "At Garment Facility "
        if self.tannery_dispatched:
            return f"This item is currently dispatched to {self.dispatch_to}"
        if self.tannery_arrived:
            return "At Tannery"
        if self.trader_dispatched:
            return "Dispatched to Tannery"
        if self.trader_arrived:
            return "With Trader"
        return "In Slaughterhouse"

    @staticmethod
    def generate_unique_new_tag():
        while True:
            new_tag = get_random_string(8, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            if not TagGeneration.objects.filter(new_tag=new_tag).exists():
                return new_tag

    def clean(self):
        if 'Other' in self.get_product_types_list() and not self.other_product_type:
            raise ValidationError("Please specify 'Other' product type")
        if self.g_date and self.g_date > timezone.now():
            raise ValidationError("Process date cannot be in the future")

    def get_leather_type(self):
        if self.animal_type in ['Cow', 'Buffalo', 'Camel', 'Beef']:
            return 'Hide'
        elif self.animal_type in ['Sheep', 'Goat', 'Mutton']:
            return 'Skin'
        return None

    def save(self, *args, **kwargs):
        if self.garment_product and not self.garment_dispatched:
            self.garment_dispatched = timezone.now()
            self.dispatch_to = "Garment Factory"
        super().save(*args, **kwargs)

    def get_product_types_list(self):
        return self.product_types.split(',') if self.product_types else []


class TransactionLog(models.Model):
    ACTION_CHOICES = (
        ('arrived', 'Arrived'),
        ('dispatched', 'Dispatched'),
        ('data_entered', 'Data Entered'),
    )
    tannery_stamp_code = models.CharField(max_length=20, null=True, blank=True)
    new_tag = models.ForeignKey(
        TagGeneration,
        related_name='transaction_logs',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    garment_product = models.ForeignKey(
        GarmentProduct,
        related_name='transaction_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(null=True, blank=True)
    actor_type = models.CharField(max_length=20)
    location = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.actor_type} {self.action} by {self.user.username}"