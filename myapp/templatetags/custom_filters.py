# custom_filters.py
from django import template
from django.forms import Select
from django.forms import BoundField

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    if isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css_class})
    return field

@register.filter(name='is_select')
def is_select(field):
    return isinstance(field.field.widget, Select)