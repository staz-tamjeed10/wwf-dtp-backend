from .models import (
    Tannery, Hd, MemberAccountType, OffalCollector, Member,
    CashEntry, Tag, GarmentProduct
)
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import TagGeneration, Confirmation, TransactionLog
from django.utils import timezone
import pytz
from myapp.serializers import ProfileSerializer


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class ConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Confirmation
        fields = '__all__'


class TagGenerationSerializer(serializers.ModelSerializer):
    current_status = serializers.SerializerMethodField()
    tannage_type = serializers.ChoiceField(
        choices=TagGeneration.TANNAGE_TYPE_CHOICES,
        required=False,
        allow_null=True
    )
    tannery_name = serializers.SerializerMethodField()
    tannery_location = serializers.SerializerMethodField()
    product_types = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TagGeneration
        fields = '__all__'

    def get_current_status(self, obj):
        if obj.garment_dispatched:
            return "Dispatched from Garment"
        if obj.garment_arrived:
            return "At Garment Facility"
        if obj.tannery_dispatched:
            return f"This item is currently dispatched to '{obj.dispatch_to}'"
        if obj.tannery_arrived:
            return "At Tannery"
        if obj.trader_dispatched:
            return "Dispatched to Tannery"
        if obj.trader_arrived:
            return "With Trader"
        return "In Slaughterhouse"

    def get_tannery_name(self, obj):
        tannery_log = obj.transaction_logs.filter(
            actor_type='tannery',
            action='arrived'
        ).first()
        if tannery_log and tannery_log.user and tannery_log.user.profile:
            return tannery_log.user.profile.full_name
        return None

    def get_tannery_location(self, obj):
        tannery_log = obj.transaction_logs.filter(
            actor_type='tannery',
            action='arrived'
        ).first()
        if tannery_log and tannery_log.user and tannery_log.user.profile:
            return tannery_log.user.profile.city
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('product_types'):
            representation['product_types'] = representation['product_types'].split(',')
        else:
            representation['product_types'] = []
        return representation

    def to_internal_value(self, data):
        if 'product_types' in data and isinstance(data['product_types'], list):
            data['product_types'] = ','.join(data['product_types'])
        return super().to_internal_value(data)


class LeatherTagSerializer(serializers.Serializer):
    s_no = serializers.IntegerField()
    batch_no = serializers.CharField()
    total_animals = serializers.IntegerField()
    command = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    owner_name = serializers.CharField()
    expiry_days = serializers.IntegerField()
    account_type = serializers.CharField()
    offal_collector = serializers.CharField()
    datetime = serializers.CharField()
    product_code = serializers.CharField()
    rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_tags = serializers.IntegerField()
    total_prints = serializers.IntegerField()
    print_on_roll = serializers.BooleanField()
    tags_generated = serializers.BooleanField()
    tag_ids = serializers.ListField(child=serializers.CharField())


class TransactionLogSerializer(serializers.ModelSerializer):
    pakistan_time = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    location = serializers.SerializerMethodField()

    class Meta:
        model = TransactionLog
        fields = '__all__'

    def get_pakistan_time(self, obj):
        if obj.timestamp:
            tz = pytz.timezone('Asia/Karachi')
            return timezone.localtime(obj.timestamp, timezone=tz)
        return None

    def get_location(self, obj):
        # Get location from user's profile
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile:
            return obj.user.profile.city, (", Pakistan")
        return None


class TannerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tannery
        fields = '__all__'


class HdSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product_types = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Hd
        fields = '__all__'
        extra_kwargs = {
            'animal_id': {'read_only': True},
            'g_date': {'required': False},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('product_types'):
            representation['product_types'] = representation['product_types'].split(',')
        else:
            representation['product_types'] = []
        return representation

    def to_internal_value(self, data):
        if 'product_types' in data and isinstance(data['product_types'], list):
            data['product_types'] = ','.join(data['product_types'])
        return super().to_internal_value(data)


class MemberAccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberAccountType
        fields = '__all__'


class OffalCollectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffalCollector
        fields = '__all__'


class MemberSerializer(serializers.ModelSerializer):
    account_type = MemberAccountTypeSerializer(read_only=True)

    class Meta:
        model = Member
        fields = '__all__'


class CashEntrySerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    offal_collector = OffalCollectorSerializer(read_only=True)

    class Meta:
        model = CashEntry
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    confirmation = ConfirmationSerializer(read_only=True)

    class Meta:
        model = Tag
        fields = '__all__'


class GarmentProductSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product_types = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = GarmentProduct
        fields = '__all__'
        extra_kwargs = {
            'garment_id': {'read_only': True},
            'g_date': {'required': False},
        }

    def validate_product_types(self, value):
        if value:
            # Check if the value looks corrupted (individual characters)
            if len(value) == 1 or (',' in value and all(len(item) == 1 for item in value.split(','))):
                raise serializers.ValidationError("Invalid product types format. Expected comma-separated product names.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('product_types'):
            representation['product_types'] = representation['product_types'].split(',')
        else:
            representation['product_types'] = []
        return representation

    def to_internal_value(self, data):
        if 'product_types' in data and isinstance(data['product_types'], list):
            # Validate that each item is a valid product type
            valid_types = [choice[0] for choice in GarmentProduct.PRODUCT_TYPE_CHOICES]
            for product_type in data['product_types']:
                if product_type not in valid_types and product_type != 'Other':
                    raise serializers.ValidationError(f"Invalid product type: {product_type}")
            data['product_types'] = ','.join(data['product_types'])
        return super().to_internal_value(data)


class TraceResultSerializer(serializers.Serializer):
    type = serializers.CharField()
    data = serializers.DictField()
    garment = serializers.DictField(required=False)
    transactions = serializers.ListField(required=False)
    tags = serializers.ListField(required=False)