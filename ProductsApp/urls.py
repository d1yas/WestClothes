from django.urls import path
from .views import (
    # Public pages
    HomePageView,
    CatalogPageView,
    # Public API
    ProductListAPIView,
    ProductDetailAPIView,
    CategoryListAPIView,
    SubCategoryListAPIView,
    SizeListAPIView,
    # Auth
    AdminLoginView,
    AdminLogoutView,
    # Admin panel
    AdminPanelView,
    AdminProductCreateView,
    AdminProductUpdateView,
    AdminProductDeleteView,
    SendOrderAPIView,
)

urlpatterns = [
    # ── Публичные страницы ────────────────────────────
    path('',                          HomePageView.as_view(),         name='index'),
    path('catalog/',                  CatalogPageView.as_view(),      name='catalog'),

    # ── Публичный API ──────────────────────────────────
    path('api/products/',              ProductListAPIView.as_view(),   name='api_products'),
    path('api/products/<int:pk>/',     ProductDetailAPIView.as_view(), name='api_product_detail'),
    path('api/categories/',            CategoryListAPIView.as_view(),  name='api_categories'),
    path('api/subcategories/',         SubCategoryListAPIView.as_view(), name='api_subcategories'),
    path('api/products/sizes/',        SizeListAPIView.as_view(),      name='api_sizes'),
    path('api/send_order/',            SendOrderAPIView.as_view(),     name='api_send_order'),

    # ── Авторизация ────────────────────────────────────
    path('admin/login',                AdminLoginView.as_view(),       name='admin_login'),
    path('admin/logout',               AdminLogoutView.as_view(),      name='admin_logout'),

    # ── Панель управления ──────────────────────────────
    path('admin/panel',                AdminPanelView.as_view(),       name='admin_panel'),

    # ── CRUD товаров ───────────────────────────────────
    path('admin/products/add',         AdminProductCreateView.as_view(), name='admin_product_add'),
    path('admin/products/<int:pk>/edit',   AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('admin/products/<int:pk>/delete', AdminProductDeleteView.as_view(), name='admin_product_delete'),
]
