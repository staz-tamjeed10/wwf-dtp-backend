from django import forms
from .models import Hd, Tannery
from django.core.exceptions import ValidationError


class HdForm(forms.ModelForm):
    product_types = forms.MultipleChoiceField(
        choices=Hd.PRODUCT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    other_product_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Specify other product type'})
    )

    class Meta:
        model = Hd
        fields = '__all__'
        widgets = {
            'slaughter_date': forms.DateInput(attrs={'type': 'date'}),
            'trader_arrived': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'trader_dispatched': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'tannery_arrived': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'tannery_dispatched': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'garment_arrived': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'garment_dispatched': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'g_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tannery'].queryset = Tannery.objects.all()

        if self.instance and self.instance.product_types:
            self.initial['product_types'] = self.instance.get_product_types_list()

    def clean(self):
        cleaned_data = super().clean()
        product_types = cleaned_data.get('product_types', [])
        other_product = cleaned_data.get('other_product_type')

        if 'Other' in product_types and not other_product:
            self.add_error('other_product_type', 'This field is required when selecting "Other"')

        cleaned_data['product_types'] = ','.join(product_types) if product_types else None
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.product_types = self.cleaned_data.get('product_types')
        if commit:
            instance.save()
            self.save_m2m()
        return instance
