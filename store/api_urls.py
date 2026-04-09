from django.contrib import admin
from django.urls import path,include
from rest_framework import routers

from .api_views import (
    CategoryViewSet,
    BrandViewSet,
    ProductViewSet,
    CartViewSet,
    OrderViewSet,
)

router=routers.DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('',include(router.urls))
]


