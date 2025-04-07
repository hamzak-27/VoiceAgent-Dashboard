from django import template

register = template.Library()

@register.filter
def divisibleby(value, arg):
    """Returns the integer division of the value by the argument"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def modulo(value, arg):
    """Returns the remainder of the division"""
    try:
        return int(value) % int(arg)
    except (ValueError, ZeroDivisionError):
        return 0