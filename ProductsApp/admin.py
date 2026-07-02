from django.contrib import admin
from .models import Product, Category, SubCategory, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'slug', 'icon', 'order', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name', 'slug', 'description')
    list_editable = ('order', 'is_active')
    ordering      = ('order', 'name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'slug', 'category', 'order', 'is_active')
    list_filter   = ('category', 'is_active')
    search_fields = ('name', 'slug', 'description')
    list_editable = ('order', 'is_active')
    ordering      = ('category', 'order', 'name')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'category', 'subcategory', 'price', 'badge', 'in_stock', 'created_at')
    list_filter   = ('category', 'subcategory', 'badge', 'in_stock')
    search_fields = ('name', 'description')
    list_editable = ('price', 'in_stock', 'badge')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('category', 'subcategory')
    inlines = [ProductImageInline]
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'category', 'subcategory', 'description', 'price', 'discount_percent'),
        }),
        ('Параметры', {
            'fields': ('badge', 'in_stock', '_sizes'),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
