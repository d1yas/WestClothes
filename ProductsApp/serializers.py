from rest_framework import serializers
from .models import Product, Category, SubCategory, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories list with nested subcategories"""
    subcategories_count = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'order', 'subcategories_count', 'subcategories']

    def get_subcategories_count(self, obj):
        return obj.subcategories.filter(is_active=True).count()

    def get_subcategories(self, obj):
        subs = obj.subcategories.filter(is_active=True).order_by('order', 'name')
        return SubCategorySerializer(subs, many=True).data


class SubCategorySerializer(serializers.ModelSerializer):
    """Serializer for subcategories"""
    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category', 'description', 'order']


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'order']

    def get_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ''


class ProductSerializer(serializers.ModelSerializer):
    """Public API serializer for products."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_slug = serializers.SlugField(source='subcategory.slug', read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id',
            'name',
            'category',
            'category_name',
            'category_slug',
            'subcategory',
            'subcategory_name',
            'subcategory_slug',
            'description',
            'price',
            'discount_percent',
            'badge',
            'in_stock',
            'images',
            'sizes',
        ]

    def get_images(self, obj):
        # Список URL-адресов фото товара (по порядку)
        urls = []
        for pi in obj.product_images.all():
            try:
                urls.append(pi.image.url)
            except ValueError:
                continue
        return urls


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Сериалайзер для записи (админ-панель). Фото загружаются отдельно через views.
    """
    sizes = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    sizes_raw = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=''
    )
    discount_percent = serializers.IntegerField(
        required=False, min_value=0, max_value=100, default=0
    )

    class Meta:
        model  = Product
        fields = [
            'id',
            'name',
            'category',
            'subcategory',
            'description',
            'price',
            'discount_percent',
            'badge',
            'in_stock',
            'sizes',
            'sizes_raw',
        ]

    def _parse_sizes(self, raw: str) -> list[str]:
        return [s.strip() for s in raw.split(',') if s.strip()] if raw else []

    def _merge_sizes(self, validated_data: dict) -> dict:
        raw = validated_data.pop('sizes_raw', '')
        sizes = validated_data.get('sizes', []) or []
        merged = []
        for size in sizes + self._parse_sizes(raw):
            if size and size not in merged:
                merged.append(size)
        validated_data['sizes'] = merged
        return validated_data

    def create(self, validated_data):
        validated_data = self._merge_sizes(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._merge_sizes(validated_data)
        return super().update(instance, validated_data)
