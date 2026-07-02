from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count, Q
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import urllib.request
import urllib.parse

import json

from .models import Product, Category, SubCategory, ProductImage, Order
from .serializers import ProductSerializer, ProductWriteSerializer, CategorySerializer, SubCategorySerializer


# ─────────────────────────────────────────────
# PUBLIC PAGES (главная страница и каталог)
# ─────────────────────────────────────────────

class HomePageView(View):
    """
    GET /  → показывает главную страницу (home.html)
    """
    template_name = 'home.html'

    def get(self, request):
        # Передаём опциональный Telegram-юзернейм администратора в шаблон
        return render(request, self.template_name, {
            'admin_tg': getattr(settings, 'ADMIN_TG_USERNAME', ''),
        })


class CatalogPageView(View):
    """
    GET /catalog/  → показывает каталог товаров (catalog.html)
    """
    template_name = 'catalog.html'

    def get(self, request):
        # Передаём опциональный Telegram-юзернейм и numeric id администратора
        return render(request, self.template_name, {
            'admin_tg': getattr(settings, 'ADMIN_TG_USERNAME', ''),
            'admin_tg_id': getattr(settings, 'ADMIN_TG_ID', ''),
        })


# ─────────────────────────────────────────────
# PUBLIC API  (используется index.html)
# ─────────────────────────────────────────────

class ProductListAPIView(APIView):
    """
    GET /api/products/
    Returns all products for public catalog.
    Supports query parameters:
      ?category=<slug>
      ?subcategory=<slug>
      ?badge=new|hot|sale
      ?in_stock=true
      ?search=text
    """

    def get(self, request):
        qs = Product.objects.all().select_related('category', 'subcategory')

        category_slug = request.query_params.get('category')
        subcategory_slug = request.query_params.get('subcategory')
        badge    = request.query_params.get('badge')
        in_stock = request.query_params.get('in_stock')
        search   = request.query_params.get('search', '').strip()

        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if subcategory_slug:
            qs = qs.filter(subcategory__slug=subcategory_slug)
        if badge:
            qs = qs.filter(badge=badge)
        if in_stock is not None:
            qs = qs.filter(in_stock=in_stock.lower() == 'true')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)


class ProductDetailAPIView(APIView):
    """
    GET /api/products/<id>/
    """

    def get(self, request, pk):
        product    = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class CategoryListAPIView(APIView):
    """
    GET /api/categories/
    Returns list of active categories with their subcategories.
    """

    def get(self, request):
        categories = Category.objects.filter(is_active=True).prefetch_related(
            'subcategories'
        ).order_by('order', 'name')
        serializer = CategorySerializer(categories, many=True)
        return Response({'categories': serializer.data})


class SubCategoryListAPIView(APIView):
    """
    GET /api/subcategories/?category=<slug>
    Returns list of subcategories for a specific category.
    """

    def get(self, request):
        category_slug = request.query_params.get('category')
        if category_slug:
            subcategories = SubCategory.objects.filter(
                category__slug=category_slug,
                is_active=True
            ).order_by('order', 'name')
        else:
            subcategories = SubCategory.objects.filter(is_active=True).order_by('order', 'name')
        
        serializer = SubCategorySerializer(subcategories, many=True)
        return Response({'subcategories': serializer.data})


class SizeListAPIView(APIView):
    """
    GET /api/products/sizes/
    Возвращает список уникальных размеров из всех товаров.
    """

    def get(self, request):
        sizes_set: set[str] = set()
        for product in Product.objects.all():
            sizes_set.update(product.sizes)
        return Response({'sizes': sorted(sizes_set)})


# ─────────────────────────────────────────────
# ADMIN  —  сессионный вход (login.html)
# ─────────────────────────────────────────────

class AdminLoginView(View):
    """
    GET  /admin/login  → показывает login.html
    POST /admin/login  → проверяет пароль, редиректит в панель
    """
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('admin_panel')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Проверка на пустые поля
        if not username or not password:
            return render(request, self.template_name, {'error': 'Заполните все поля'})
        
        # Попытка аутентификации
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            # Проверяем, существует ли пользователь
            try:
                User.objects.get(username=username)
                # Пользователь существует, но пароль неверный
                return render(request, self.template_name, {'error': 'Неверный пароль'})
            except User.DoesNotExist:
                # Пользователь не найден
                return render(request, self.template_name, {'error': 'Пользователь не найден'})
        
        # Проверяем права доступа
        if user.is_staff:
            login(request, user)
            return redirect('admin_panel')
        else:
            return render(request, self.template_name, {'error': 'У вас нет прав доступа'})


class AdminLogoutView(View):
    """GET /admin/logout"""

    def get(self, request):
        logout(request)
        return redirect('admin_login')


# ─────────────────────────────────────────────
# ADMIN PANEL  (panel.html)
# ─────────────────────────────────────────────

SIZES_ALL = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminPanelView(View):
    """
    GET /admin/panel  → рендерит panel.html с данными
    """
    template_name = 'panel.html'

    def _get_context(self, request):
        search_id = request.GET.get('search_id', '').strip()
        order_product_id = request.GET.get('product_id', '').strip()
        order_size = request.GET.get('size', '').strip()
        order_name = request.GET.get('name', '').strip()

        products = Product.objects.all().select_related('category', 'subcategory')
        if search_id.isdigit():
            products = products.filter(id=int(search_id))

        stats = {
            'total': products.count(),
            'cats' : products.values('category').distinct().count(),
            'new'  : products.filter(badge='new').count(),
            'hot'  : products.filter(badge='hot').count(),
        }
        order_info = None
        if order_product_id and order_size:
            order_info = {
                'id': order_product_id,
                'name': order_name,
                'size': order_size,
            }
        
        # Get all categories and subcategories for the admin panel
        categories = Category.objects.filter(is_active=True).order_by('order', 'name')
        categories_data = []
        for cat in categories:
            subcats = cat.subcategories.filter(is_active=True).order_by('order', 'name')
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'subcategories': [{'id': s.id, 'name': s.name} for s in subcats]
            })
        
        # Сериализованные продукты для JS (openEdit)
        products_json = json.dumps([
            {
                'id': p.id,
                'name': p.name,
                'category': p.category.id,
                'category_name': p.category.name,
                'subcategory': p.subcategory.id if p.subcategory else None,
                'subcategory_name': p.subcategory.name if p.subcategory else '',
                'description': p.description,
                'price': p.price,
                'discount_percent': p.discount_percent,
                'badge': p.badge,
                'in_stock': p.in_stock,
                'images': p.images,
                'sizes': p.sizes,
            }
            for p in products
        ], ensure_ascii=False)
        return {
            'products' : products,
            'products_json': products_json,
            'stats'    : stats,
            'sizes_all': SIZES_ALL,
            'sizes_all_json': json.dumps(SIZES_ALL),
            'search_id': search_id,
            'order_info': order_info,
            'categories_json': json.dumps(categories_data, ensure_ascii=False),
        }

    def get(self, request):
        return render(request, self.template_name, self._get_context(request))


# ─────────────────────────────────────────────
# ADMIN API — CRUD товаров (из panel.html)
# ─────────────────────────────────────────────

@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductCreateView(APIView):
    """
    POST /admin/products/add
    Принимает данные HTML-формы (multipart) с файлами images[].
    Минимум 1, максимум 6 фото.
    """

    def post(self, request):
        data = self._parse_form(request)
        files = request.FILES.getlist('images')

        if len(files) < 1:
            return self._fail(request, 'Загрузите минимум 1 фото товара')
        if len(files) > Product.MAX_IMAGES:
            return self._fail(request, f'Максимум {Product.MAX_IMAGES} фото')

        serializer = ProductWriteSerializer(data=data)

        if serializer.is_valid():
            product = serializer.save()
            for i, f in enumerate(files):
                ProductImage.objects.create(product=product, image=f, order=i)
            if self._is_browser(request):
                return redirect('admin_panel')
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self._is_browser(request):
            return redirect('admin_panel')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _fail(request, message):
        if AdminProductCreateView._is_browser(request):
            return redirect('admin_panel')
        return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _parse_form(request) -> dict:
        # DRF QueryDict → plain dict
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = dict(request.data)

        # sizes приходят как список из чекбоксов
        data['sizes'] = request.data.getlist('sizes', [])

        # in_stock: если чекбокс есть в запросе → True
        data['in_stock'] = 'in_stock' in request.data

        return data

    @staticmethod
    def _is_browser(request) -> bool:
        if hasattr(request, 'accepted_media_type'):
            return 'text/html' in request.accepted_media_type
        return True


class SendOrderAPIView(APIView):
    """
    POST /api/send_order/
    Accepts JSON: { product_id, name, size, price, contact (optional), customer_name (optional) }
    Order всегда сохраняется в БД. Telegram-уведомление отправляется, если настроен бот.
    """

    def post(self, request):
        data = request.data if hasattr(request, 'data') else request.POST

        product_id = data.get('product_id')
        name = (data.get('name') or '').strip()
        size = (data.get('size') or '').strip()
        price = (data.get('price') or '').strip()
        contact = (data.get('contact') or '').strip()
        customer_name = (data.get('customer_name') or '').strip()

        if not name:
            return Response({'ok': False, 'detail': 'product name is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        product = None
        if product_id:
            try:
                product = Product.objects.get(pk=int(product_id))
            except (ValueError, Product.DoesNotExist):
                product = None

        order = Order.objects.create(
            product=product,
            product_name=name,
            size=size,
            price=price,
            customer_name=customer_name,
            contact=contact,
        )

        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        admin_chat = getattr(settings, 'ADMIN_TG_ID', '')

        if bot_token and admin_chat:
            size_part = f" | Размер: {size}" if size else ''
            contact_part = f"\n📞 Контакт: {contact}" if contact else ''
            text = (
                f"🛒 Новый заказ #{order.id}\n\n"
                f"👕 {name}{size_part}\n"
                f"💰 Цена: {price}"
                f"{contact_part}"
            )
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {'chat_id': admin_chat, 'text': text}
            data_encoded = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data_encoded)
            try:
                urllib.request.urlopen(req, timeout=10)
                order.telegram_sent = True
                order.save(update_fields=['telegram_sent'])
            except Exception as e:
                order.telegram_error = str(e)[:500]
                order.save(update_fields=['telegram_error'])

        return Response({'ok': True, 'order_id': order.id}, status=status.HTTP_200_OK)


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductUpdateView(APIView):
    """
    POST /admin/products/<id>/edit
    Опционально принимает новые файлы images[] — если переданы, заменяют все старые.
    Также принимает remove_image_ids (список id для удаления) и галочку replace_images.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = AdminProductCreateView._parse_form(request)
        new_files = request.FILES.getlist('images')
        remove_ids = request.POST.getlist('remove_image_ids')

        # Validate that at least one image remains
        current_count = product.product_images.count()
        kept_count = current_count - len([rid for rid in remove_ids if rid])
        future_count = kept_count + len(new_files)
        if future_count < 1:
            return AdminProductCreateView._fail(request, 'Должно остаться минимум 1 фото')
        if future_count > Product.MAX_IMAGES:
            return AdminProductCreateView._fail(
                request, f'Максимум {Product.MAX_IMAGES} фото'
            )

        serializer = ProductWriteSerializer(product, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()

            if remove_ids:
                product.product_images.filter(
                    id__in=[int(x) for x in remove_ids if x.isdigit()]
                ).delete()

            if new_files:
                last_order = product.product_images.count()
                for i, f in enumerate(new_files):
                    ProductImage.objects.create(
                        product=product, image=f, order=last_order + i
                    )

            if AdminProductCreateView._is_browser(request):
                return redirect('admin_panel')
            return Response(serializer.data)

        if AdminProductCreateView._is_browser(request):
            return redirect('admin_panel')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductDeleteView(APIView):
    """
    POST /admin/products/<id>/delete
    DELETE /admin/products/<id>/delete  (для REST-клиентов)
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        if AdminProductCreateView._is_browser(request):
            return redirect('admin_panel')
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, pk):
        return self.post(request, pk)
