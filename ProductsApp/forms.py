from django import forms
from .models import Product


class SizeMultipleChoiceField(forms.MultipleChoiceField):
    """Custom field for selecting multiple sizes via checkboxes"""

    def __init__(self, *args, **kwargs):
        # Стандартные размеры
        SIZE_CHOICES = [
            ('XS', 'XS'),
            ('S', 'S'),
            ('M', 'M'),
            ('L', 'L'),
            ('XL', 'XL'),
            ('XXL', 'XXL'),
            ('3XL', '3XL'),
            ('38', '38'),
            ('39', '39'),
            ('40', '40'),
            ('41', '41'),
            ('42', '42'),
            ('43', '43'),
            ('44', '44'),
            ('45', '45'),
            ('46', '46'),
        ]
        kwargs['choices'] = SIZE_CHOICES
        kwargs['widget'] = forms.CheckboxSelectMultiple
        kwargs['required'] = False
        super().__init__(*args, **kwargs)


class ProductAdminForm(forms.ModelForm):
    """Custom form for Product admin with size checkboxes"""

    sizes = SizeMultipleChoiceField(
        label='Размеры',
        help_text='Выберите доступные размеры для этого товара'
    )

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Загружаем сохраненные размеры из JSON
            self.initial['sizes'] = self.instance.sizes

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Сохраняем выбранные размеры в JSON-поле
        instance.sizes = self.cleaned_data.get('sizes', [])
        if commit:
            instance.save()
        return instance
