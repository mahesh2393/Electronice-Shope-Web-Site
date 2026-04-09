from django.contrib import admin
from .models import (
    Product, Category, Brand, Order, OrderItem, Cart, CustomProduct, WhatsAppInquiry, Profile
)


# ===== SIMPLE REGISTRATIONS =====
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Cart)
admin.site.register(CustomProduct)
admin.site.register(WhatsAppInquiry)
admin.site.register(Profile)
admin.site.register(Product)


# ===== ORDER ADMIN WITH INLINE =====
class OrderItemInline(admin.TabularInline):
    """Display Order Items inside Order Admin"""
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'subtotal']
    can_delete = False
    
    def subtotal(self, obj):
        return obj.quantity * obj.price
    subtotal.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order Admin with Items"""
    list_display = ['id', 'tracking_number', 'name', 'email', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['id', 'tracking_number', 'name', 'email', 'phone']
    list_editable = ['status']
    readonly_fields = ['tracking_number', 'tracking_id', 'created_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order Item Admin"""
    list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
    list_filter = ['order']
    search_fields = ['product__name', 'order__id']
    
    def subtotal(self, obj):
        return obj.quantity * obj.price
    subtotal.short_description = 'Subtotal'





