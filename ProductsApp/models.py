import json
from django.db import models


class Category(models.Model):
    """Main clothing categories: Upper Wear, Lower Wear, Shoes, Accessories"""
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('URL', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True, default='')
    icon = models.CharField('Иконка (emoji)', max_length=10, default='👕')
    order = models.PositiveIntegerField('Порядок', default=0, help_text='Меньше = выше')
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    """Sub-categories: T-shirts, Shirts, Jackets, etc."""
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('URL', max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name='Категория')
    description = models.TextField('Описание', blank=True, default='')
    order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Подкатегория'
        verbose_name_plural = 'Подкатегории'
        ordering = ['order', 'name']
        unique_together = ['category', 'slug']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class Product(models.Model):
    BADGE_CHOICES = [
        ('',    'Нет'),
        ('new', 'Новинка'),
        ('hot', 'Хит'),
        ('sale', 'Скидка'),
    ]
    MAX_IMAGES = 6

    name             = models.CharField('Название', max_length=255)
    category         = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='Категория')
    subcategory      = models.ForeignKey(SubCategory, on_delete=models.PROTECT, related_name='products', verbose_name='Подкатегория', null=True, blank=True)
    description      = models.TextField('Описание', blank=True, default='')
    price            = models.PositiveIntegerField('Цена (сум)')
    discount_percent = models.PositiveSmallIntegerField('Скидка (%)', default=0)
    badge            = models.CharField('Значок', max_length=10, choices=BADGE_CHOICES, blank=True, default='')
    in_stock         = models.BooleanField('В наличии', default=True)

    # Размеры по-прежнему храним как JSON-строку (простой массив)
    _sizes  = models.TextField('Размеры (JSON)', db_column='sizes', blank=True, default='[]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def sizes(self) -> list[str]:
        try:
            return json.loads(self._sizes) or []
        except (ValueError, TypeError):
            return []

    @sizes.setter
    def sizes(self, value: list[str]):
        self._sizes = json.dumps(value, ensure_ascii=False)

    @property
    def images(self) -> list[str]:
        """URL-адреса картинок товара (медиа). Если нет — пустой список."""
        return [pi.image.url for pi in self.product_images.all() if pi.image]

    class Meta:
        verbose_name        = 'Товар'
        verbose_name_plural = 'Товары'
        ordering            = ['-created_at']

    def __str__(self):
        return self.name


def product_image_path(instance, filename):
    return f'products/{instance.product_id}/{filename}'


class ProductImage(models.Model):
    """Фото товара. Хранятся локально в MEDIA_ROOT/products/<id>/."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images', verbose_name='Товар')
    image   = models.ImageField('Файл', upload_to=product_image_path)
    order   = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Фото товара'
        verbose_name_plural = 'Фото товаров'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.product.name} #{self.order}'


class Order(models.Model):
    """Заказ от клиента — сохраняется всегда, в Telegram отправляется опционально."""
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В обработке'),
        ('done', 'Выполнен'),
        ('cancelled', 'Отменён'),
    ]

    product   = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Товар')
    product_name = models.CharField('Название товара', max_length=255)
    size      = models.CharField('Размер', max_length=10, blank=True, default='')
    price     = models.CharField('Цена (как показано)', max_length=64, blank=True, default='')
    customer_name = models.CharField('Имя клиента', max_length=255, blank=True, default='')
    contact   = models.CharField('Контакт', max_length=255, blank=True, default='')
    status    = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    telegram_sent = models.BooleanField('Отправлено в Telegram', default=False)
    telegram_error = models.CharField('Ошибка Telegram', max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.id} — {self.product_name} ({self.size or "—"})'
