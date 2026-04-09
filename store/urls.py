from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/',views.login_view,name='login'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('process-payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'), 
    path('whatsapp-inquiry/', views.whatsapp_inquiry, name='whatsapp_inquiry'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path('track-order/', views.track_order_by_number, name='track_order_by_number'),
    path('api/', include('store.api_urls')),  # API
    path('profile/', views.profile_view, name='profile'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('about/', views.about_us, name='about_us'),
    path('contact/', views.contact_us, name='contact_us'),
    # Logout URL
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard',views.admin_dashboard,name='admin_dashboard'),
    
    # Stock Management URLs
    path('stock/dashboard/', views.stock_dashboard, name='stock_dashboard'),
    path('stock/list/', views.stock_list, name='stock_list'),
    path('stock/update/<int:product_id>/', views.stock_update, name='stock_update'),
    path('stock/movements/', views.stock_movements, name='stock_movements'),
    path('stock/export/', views.stock_export, name='stock_export'),
    path('stock/bulk-update/', views.stock_bulk_update, name='stock_bulk_update'),
    path('/add-product/', views.add_product, name='add_product'),
    path('/orders/',views.orders, name='orders'),
    path('/orders_detail/<int:order_id>/',views.orders_detail,name='orders_detail'),
    
    # User Management URLs
    path('users/', views.users, name='users'),
    path('block/<int:user_id>/', views.admin_block_user, name='admin_block_user'),
    path('unblock/<int:user_id>/', views.admin_unblock_user, name='admin_unblock_user'),
    path('delete/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
]