from django import forms
from welc.models import TagGeneration

class EditQRForm(forms.ModelForm):
    class Meta:
        model = TagGeneration
        fields = [
            'owner_name', 'batch_no'
        ]

class EmailQRForm(forms.Form):
    email = forms.EmailField(label="Recipient Email", widget=forms.EmailInput(attrs={'placeholder': 'Enter email'}))
