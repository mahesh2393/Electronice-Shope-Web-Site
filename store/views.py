from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum, F, Count
from django.db.models.functions import TruncMonth
from .models import Product, Brand, Cart, Order, OrderItem, WhatsAppInquiry, StockMovement, Category, Profile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse
import os,json
from decimal import Decimal



# ==================== HOME & PRODUCTS ====================

def home(request):
    # ✅ If admin is trying to access home, redirect to stock dashboard
    if request.user.is_authenticated and request.user.is_staff and request.user.username == 'mahesh':
        return redirect('stock_dashboard')
    
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    else:
        products = Product.objects.all()
    return render(request, 'home.html', {'products': products})


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'product_detail.html', {'product': product})


# ==================== CART SYSTEM ====================

def add_to_cart(request, product_id):
    """Add product to cart - Redirect to login if not authenticated"""
    # ✅ Check if user is logged in
    if not request.user.is_authenticated:
        # Store the product URL in session to redirect back after login
        request.session['next_url'] = request.path
        messages.warning(request, 'Please login to add items to cart!')
        return redirect('login')
    
    product = get_object_or_404(Product, id=product_id)
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        cart_item.quantity += 1
    else:
        cart_item.quantity = 1
    
    cart_item.save()
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('cart')

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = 0
    for item in cart_items:
        item.subtotal = item.product.price * item.quantity
        total += item.product.price * item.quantity
    context = {
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'cart.html', context)



@login_required
def update_cart(request, product_id):
    if request.method == "POST":
        cart_item = get_object_or_404(Cart, user=request.user, product_id=product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                new_subtotal = float(cart_item.product.price * cart_item.quantity)
                cart_items = Cart.objects.filter(user=request.user)
                new_total = sum(item.product.price * item.quantity for item in cart_items)
                return JsonResponse({
                    'success': True,
                    'new_subtotal': f"{new_subtotal:.2f}",
                    'new_total': f"{new_total:.2f}"
                })
            return redirect('cart')
        else:
            cart_item.delete()
        return redirect('cart')
    return redirect('cart')


@login_required
def remove_from_cart(request, product_id):
    if request.method == "POST":
        cart_item = Cart.objects.filter(user=request.user, product_id=product_id)
        cart_item.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_items = Cart.objects.filter(user=request.user)
            new_total = sum(item.product.price * item.quantity for item in cart_items)
            return JsonResponse({
                'success': True,
                'new_total': f"{new_total:.2f}"
            })
        return redirect('cart')
    return redirect('cart')


# ==================== BRAND & CATEGORY ====================

def brand_led_tv(request, brand_id):
    brands = Brand.objects.all()
    selected_brand = get_object_or_404(Brand, id=brand_id)
    products = Product.objects.filter(
        category='LED TV',
        brand=selected_brand
    )
    return render(request, 'led_tv.html', {
        'brands': brands,
        'products': products,
        'selected_brand': selected_brand
    })


# ==================== AUTH SYSTEM ====================

def signup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('signup')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('signup')
        
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('signup')
        
        if len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters!")
            return redirect('signup')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        
        messages.success(request, "Account created successfully! Please login.")
        return redirect('login')
    
    return render(request, 'signup.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Admin hardcoded login
        if username == 'admin' and password == 'admin123':
            try:
                admin_user = User.objects.get(username='admin')
                if not admin_user.is_staff:
                    admin_user.is_staff = True
                    admin_user.is_superuser = True
                    admin_user.save()
            except User.DoesNotExist:
                admin_user = User.objects.create_superuser(
                    username='admin',
                    email='admin@thehamperhub.com',
                    password='admin123',
                )
            login(request, admin_user)
            messages.success(request, 'Admin logged in successfully!')
            return redirect('admin_dashboard')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # ✅ Check if user is blocked (is_active = False)
            if not user.is_active:
                messages.error(request, '⚠️ Your account has been blocked! Please contact support for assistance.')
                return render(request, 'login.html')
            
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('home')
        else:
            # ✅ Check if user exists but password wrong, or user doesn't exist
            try:
                user_exists = User.objects.get(username=username)
                if user_exists and not user_exists.is_active:
                    messages.error(request, 'Your account has been blocked! Please contact support.')
                else:
                    messages.error(request, 'Invalid username or password!')
            except User.DoesNotExist:
                messages.error(request, 'Invalid username or password!')
    
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')


# ==================== CHECKOUT & ORDERS ====================

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    
    if not cart_items:
        messages.warning(request, "Your cart is empty!")
        return redirect('cart')
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        payment_method = request.POST.get('payment_method', 'cod')
        
        if not all([name, email, phone, address, city, pincode]):
            messages.error(request, "Please fill all fields!")
            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'total': total
            })
        
        order = Order.objects.create(
            user=request.user,
            name=name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            pincode=pincode,
            total_amount=total,
            status='pending',
            payment_method=payment_method,
            payment_status='pending'
        )
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        cart_items.delete()
        messages.success(request, f'Order placed successfully! Your Tracking Number: {order.tracking_number}')
        return redirect('order_success', order_id=order.id)
    
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total': total
    })


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('product')
    return render(request, 'order_success.html', {
        'order': order,
        'order_items': order_items
    })

@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # COD Payment
    if order.payment_method == 'cod':
        order.payment_status = 'pending'
        order.save()
        messages.success(request, "Order placed successfully! You will pay at delivery.")
        return redirect('order_success', order_id=order.id)

    # UPI Payment (PhonePe / GPay / Paytm)
    elif order.payment_method == 'upi':
        upi_id = "yourupiid@oksbi"   # <-- apna UPI ID yaha daalo
        merchant_name = "MyShop"
        amount = order.total_amount
        transaction_note = f"Order #{order.id}"

        # UPI Payment Link
        upi_link = (
            f"upi://pay?pa={"7014172393@axl"}"
            f"&pn={"Mahesh"}"
            f"&am={amount}"
            f"&cu=INR"
            f"&tn={transaction_note}"
        )

        # QR Code generate
        qr = qrcode.make(upi_link)

        qr_folder = os.path.join(settings.MEDIA_ROOT, "qr_codes")
        os.makedirs(qr_folder, exist_ok=True)

        qr_filename = f"order_{order.id}.png"
        qr_path = os.path.join(qr_folder, qr_filename)
        qr.save(qr_path)

        qr_url = settings.MEDIA_URL + f"qr_codes/{qr_filename}"

        return render(request, 'payments/upi_payment.html', {
            'order': order,
            'upi_link': upi_link,
            'qr_url': qr_url
        })

    # Card / Wallet / Netbanking (dummy success)
    else:
        order.payment_status = 'completed'
        order.save()

        msg_map = {
            'card': "Payment successful via Credit/Debit Card!",
            'netbanking': "Payment successful via Net Banking!",
            'wallet': "Payment successful via Mobile Wallet!"
        }

        msg = msg_map.get(order.payment_method, "Payment successful!")
        messages.success(request, msg)
        return redirect('order_success', order_id=order.id)

@login_required
def payment_success(request):
    return render(request, 'payment_success.html')


@login_required
def payment_cancel(request):
    return render(request, 'payment_cancel.html')


# ==================== ORDER TRACKING ====================

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def my_orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('product')
    progress = order.get_status_percentage()
    return render(request, 'track_order.html', {
        'order': order,
        'order_items': order_items,
        'progress': progress,
    })


def track_order_by_number(request):
    if request.method == 'POST':
        tracking_input = request.POST.get('tracking_number')
        email = request.POST.get('email')
        
        if not tracking_input or not email:
            messages.error(request, 'Please enter tracking number/ID and email')
            return redirect('track_order_by_number')
        
        order = None
        try:
            order = Order.objects.get(tracking_number=tracking_input, email=email)
        except Order.DoesNotExist:
            try:
                order = Order.objects.get(tracking_id=tracking_input, email=email)
            except Order.DoesNotExist:
                pass
        
        if order:
            return redirect('track_order', order_id=order.id)
        else:
            messages.error(request, 'Order not found. Please check your tracking number and email.')
            return redirect('track_order_by_number')
    
    return render(request, 'track_by_number.html')


# ==================== PROFILE ====================

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    total_orders = orders.count()
    completed_orders = orders.filter(status='delivered').count()
    total_spent = orders.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    default_address = None
    last_order = orders.first()
    if last_order:
        default_address = f"{last_order.address}, {last_order.city} - {last_order.pincode}"
    elif profile.address:
        default_address = profile.address
    
    return render(request, 'profile.html', {
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
        'default_address': default_address,
        'profile': profile,
    })


@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        profile = user.profile
        
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.pincode = request.POST.get('pincode', '')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return redirect('profile')


@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect!')
            return redirect('profile')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return redirect('profile')
        
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters!')
            return redirect('profile')
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('profile')
    
    return redirect('profile')


# ==================== WHATSAPP INQUIRY ====================

def whatsapp_inquiry(request):
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        product_name = request.POST.get('product_name', '')
        message = request.POST.get('message')
        
        whatsapp_message = f"""*New Order Inquiry* 📦

*Customer:* {name}
*Phone:* {phone}
*Product:* {product_name or 'General Inquiry'}

*Message:*
{message}"""
        
        from urllib.parse import quote
        encoded_message = quote(whatsapp_message)
        phone_number = "917014172393"
        whatsapp_url = f"https://wa.me/{phone_number}?text={encoded_message}"
        
        return redirect(whatsapp_url)
    
    return render(request, 'whatsapp_inquiry.html')


# ==================== ABOUT & CONTACT ====================

def about_us(request):
    return render(request, 'about_us.html')


def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        if not name or not email or not subject or not message:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('contact_us')
        
        email_subject = f"Contact Form: {subject} - from {name}"
        email_body = f"""
        New contact form submission:
        
        Name: {name}
        Email: {email}
        Phone: {phone}
        Subject: {subject}
        
        Message:
        {message}
        
        ---
        Submitted via MGS Electronics Contact Form
        """
        
        try:
            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=True,
            )
        except:
            pass
        
        messages.success(request, f'Thank you {name}! Your message has been sent. We will get back to you soon.')
        return redirect('contact_us')
    
    return render(request, 'contact_us.html')


# ==================== STOCK MANAGEMENT ====================

# Custom decorator to check for specific admin
def admin_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.username == 'mahesh' and request.user.is_staff:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied! Only admin can access this page.')
        return redirect('login')
    return wrapper

@admin_only
def stock_dashboard(request):
    """Stock Dashboard - Only accessible by mahesh"""
    # Your existing stock_dashboard code
    products = Product.objects.all()
    
    total_products = products.count()
    total_value = products.aggregate(total=Sum(F('price') * F('stock')))['total'] or 0
    out_of_stock = products.filter(stock=0).count()
    low_stock = products.filter(stock__lte=F('low_stock_threshold'), stock__gt=0).count()
    in_stock = products.filter(stock__gt=F('low_stock_threshold')).count()
    active_products = products.filter(is_active=True).count()
    inactive_products = products.filter(is_active=False).count()
    
    low_stock_products = products.filter(stock__lte=F('low_stock_threshold')).order_by('stock')[:20]
    out_of_stock_products = products.filter(stock=0).order_by('name')[:20]
    recent_movements = StockMovement.objects.all().select_related('product', 'created_by')[:30]
    
    context = {
        'total_products': total_products,
        'total_value': total_value,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'in_stock': in_stock,
        'active_products': active_products,
        'inactive_products': inactive_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'recent_movements': recent_movements,
    }
    return render(request, 'stock_dashboard.html', context)

@staff_member_required
def stock_list(request):
    """List all products with stock"""
    products = Product.objects.all().order_by('stock')
    
    # Search
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(category__name__icontains=search) |
            Q(brand__name__icontains=search)
        )
    
    # Filter by stock status
    status_filter = request.GET.get('status')
    if status_filter == 'in_stock':
        products = products.filter(stock__gt=F('low_stock_threshold'))
    elif status_filter == 'low_stock':
        products = products.filter(stock__lte=F('low_stock_threshold'), stock__gt=0)
    elif status_filter == 'out_of_stock':
        products = products.filter(stock=0)
    elif status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by brand
    brand_id = request.GET.get('brand')
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    # Pagination
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    context = {
        'products': page_obj,
        'search': search,
        'status_filter': status_filter,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'stock_list.html', context)


@staff_member_required
def stock_update(request, product_id):
    """Update stock for a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        movement_type = request.POST.get('movement_type')
        notes = request.POST.get('notes', '')
        
        if quantity <= 0:
            messages.error(request, 'Please enter a valid quantity (greater than 0)')
            return redirect('stock_update', product_id=product_id)
        
        StockMovement.objects.create(
            product=product,
            quantity=quantity,
            movement_type=movement_type,
            notes=notes,
            created_by=request.user
        )
        
        messages.success(request, f'Stock updated successfully! New stock: {product.stock}')
        return redirect('stock_list')
    
    return render(request, 'stock_update.html', {'product': product})


@staff_member_required
def stock_movements(request):
    """View all stock movements with filters"""
    movements = StockMovement.objects.all().select_related('product', 'created_by', 'order')
    
    # Filter by date
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        movements = movements.filter(created_at__date=datetime.today().date())
    elif date_filter == 'yesterday':
        yesterday = datetime.today().date() - timedelta(days=1)
        movements = movements.filter(created_at__date=yesterday)
    elif date_filter == 'week':
        movements = movements.filter(created_at__gte=datetime.today() - timedelta(days=7))
    elif date_filter == 'month':
        movements = movements.filter(created_at__gte=datetime.today() - timedelta(days=30))
    
    # Filter by type
    type_filter = request.GET.get('type')
    if type_filter:
        movements = movements.filter(movement_type=type_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        movements = movements.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(movements, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'movements': page_obj,
        'date_filter': date_filter,
        'type_filter': type_filter,
        'search': search,
    }
    return render(request, 'stock_movements.html', context)


@staff_member_required
def stock_export(request):
    """Export stock data to CSV"""
    products = Product.objects.all().values(
        'id', 'sku', 'name', 'category__name', 'brand__name',
        'price', 'stock', 'low_stock_threshold', 'is_active'
    )
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'SKU', 'Product Name', 'Category', 'Brand', 'Price', 'Stock', 'Low Stock Threshold', 'Status', 'Active'])
    
    for product in products:
        if product['stock'] <= 0:
            status = 'Out of Stock'
        elif product['stock'] <= product['low_stock_threshold']:
            status = 'Low Stock'
        else:
            status = 'In Stock'
        
        writer.writerow([
            product['id'],
            product['sku'] or '',
            product['name'],
            product['category__name'] or '',
            product['brand__name'] or '',
            product['price'],
            product['stock'],
            product['low_stock_threshold'],
            status,
            'Yes' if product['is_active'] else 'No'
        ])
    
    return response


@staff_member_required
def stock_bulk_update(request):
    """Bulk update stock for multiple products"""
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        quantities = request.POST.getlist('quantities')
        movement_type = request.POST.get('movement_type', 'adjustment')
        notes = request.POST.get('notes', 'Bulk stock update')
        
        updated_count = 0
        for product_id, quantity in zip(product_ids, quantities):
            if quantity and int(quantity) > 0:
                product = get_object_or_404(Product, id=product_id)
                StockMovement.objects.create(
                    product=product,
                    quantity=int(quantity),
                    movement_type=movement_type,
                    notes=notes,
                    created_by=request.user
                )
                updated_count += 1
        
        messages.success(request, f'{updated_count} products updated successfully!')
        return redirect('stock_list')
    
    products = Product.objects.filter(stock__lte=F('low_stock_threshold')).order_by('stock')
    return render(request, 'stock_bulk_update.html', {'products': products})


@staff_member_required
def stock_analytics(request):
    """Stock Analytics Page"""
    products = Product.objects.all()
    
    stock_distribution = {
        'in_stock': products.filter(stock__gt=F('low_stock_threshold')).count(),
        'low_stock': products.filter(stock__lte=F('low_stock_threshold'), stock__gt=0).count(),
        'out_of_stock': products.filter(stock=0).count(),
    }
    
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_movements = StockMovement.objects.filter(created_at__gte=six_months_ago)\
        .annotate(month=TruncMonth('created_at'))\
        .values('month', 'movement_type')\
        .annotate(total=Sum('quantity'))\
        .order_by('month')
    
    top_moving = OrderItem.objects.values('product__name', 'product__id')\
        .annotate(total_sold=Sum('quantity'))\
        .order_by('-total_sold')[:10]
    
    context = {
        'stock_distribution': stock_distribution,
        'monthly_movements': monthly_movements,
        'top_moving': top_moving,
    }
    return render(request, 'stock_analytics.html', context)

@staff_member_required
def admin_dashboard(request):
    """Complete Admin Dashboard"""
    
    # ========== STATISTICS ==========
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Today's Orders
    today_orders = Order.objects.filter(created_at__range=(today_start, today_end)).count()
    
    # Total Orders
    total_orders = Order.objects.count()
    
    # Pending Orders
    pending_orders = Order.objects.filter(status='pending').count()
    
    # Total Users
    total_users = User.objects.filter(is_staff=False).count()
    
    # Total Products
    total_products = Product.objects.count()
    
    # Low Stock Products
    low_stock_count = Product.objects.filter(stock__lte=F('low_stock_threshold'), stock__gt=0).count()
    
    # ========== WEEKLY ORDERS CHART ==========
    weekly_labels = []
    weekly_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date, datetime.max.time())
        count = Order.objects.filter(created_at__range=(date_start, date_end)).count()
        weekly_labels.append(date.strftime('%a'))
        weekly_data.append(count)
    
    # ========== MONTHLY ORDERS CHART ==========
    monthly_labels = []
    monthly_data = []
    
    for i in range(5, -1, -1):
        date = today.replace(day=1) - timedelta(days=i*30)
        month_start = datetime.combine(date.replace(day=1), datetime.min.time())
        if date.month == 12:
            next_month = date.replace(year=date.year+1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month+1, day=1)
        month_end = datetime.combine(next_month - timedelta(days=1), datetime.max.time())
        
        count = Order.objects.filter(created_at__range=(month_start, month_end)).count()
        monthly_labels.append(date.strftime('%b %Y'))
        monthly_data.append(count)
    
    # ========== RECENT ORDERS ==========
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # ========== RECENT STOCK MOVEMENTS ==========
    recent_movements = StockMovement.objects.all().select_related('product').order_by('-created_at')[:10]
    
    context = {
        'today_orders': today_orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_users': total_users,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'weekly_orders': json.dumps({'labels': weekly_labels, 'data': weekly_data}),
        'monthly_orders': json.dumps({'labels': monthly_labels, 'data': monthly_data}),
        'recent_orders': recent_orders,
        'recent_movements': recent_movements,
    }
    return render(request, 'admin_dashboard.html', context)
@staff_member_required
def add_product(request):
    """Add New Product"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        price = request.POST.get('price')
        description = request.POST.get('description')
        stock = request.POST.get('stock', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        sku = request.POST.get('sku', '')
        is_active = request.POST.get('is_active') == 'true'
        is_featured = request.POST.get('is_featured') == 'true'
        image = request.FILES.get('image')
        
        # Validation
        if not name or not category_id or not brand_id or not price or not description:
            messages.error(request, 'Please fill all required fields!')
            return redirect('add_product')
        
        # Create product
        product = Product.objects.create(
            name=name,
            category_id=category_id,
            brand_id=brand_id,
            price=price,
            description=description,
            stock=stock,
            low_stock_threshold=low_stock_threshold,
            sku=sku if sku else None,
            is_active=is_active,
            is_featured=is_featured,
            image=image
        )
        
        messages.success(request, f'Product "{name}" added successfully!')
        return redirect('stock_list')
    
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    context = {
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'add_product.html', context)

@staff_member_required
def orders(request):
    """Admin Orders List"""
    orders = Order.objects.all().order_by('-created_at')
    
    # Search
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Status Filter
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Payment Filter
    payment_filter = request.GET.get('payment')
    if payment_filter:
        orders = orders.filter(payment_method=payment_filter)
    
    # Date Range Filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        orders = orders.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        orders = orders.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Statistics
    pending_count = Order.objects.filter(status='pending').count()
    processing_count = Order.objects.filter(status='processing').count()
    shipped_count = Order.objects.filter(status='shipped').count()
    delivered_count = Order.objects.filter(status='delivered').count()
    print(pending_count)
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'search': search,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'orders.html', context)


@staff_member_required
def admin_update_order_status(request, order_id):
    """Update Order Status"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS):
            order.status = new_status
            order.save()
            messages.success(request, f'Order #{order.id} status updated to {order.get_status_display()}')
        else:
            messages.error(request, 'Invalid status')
    
    return redirect('admin_orders')


@staff_member_required
def orders_detail(request, order_id):
    """Order Detail Page"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'order_detail.html', context)
@staff_member_required
def users(request):
    """Admin Users List"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Filter by status (active/blocked)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'blocked':
        users = users.filter(is_active=False)
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter == 'customer':
        users = users.filter(is_staff=False)
    elif role_filter == 'admin':
        users = users.filter(is_staff=True)
    
    # Get order count for each user
    user_data = []
    for user in users:
        # Check if user is blocked (is_active = False)
        is_blocked = not user.is_active
        
        # Count orders
        order_count = Order.objects.filter(user=user).count()
        
        user_data.append({
            'user': user,
            'order_count': order_count,
            'is_blocked': is_blocked,
        })
    
    # Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    blocked_users = User.objects.filter(is_active=False).count()
    
    # Pagination
    paginator = Paginator(user_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'search': search,
        'status_filter': status_filter,
        'role_filter': role_filter,
    }
    return render(request, 'users.html', context)


@staff_member_required
def admin_block_user(request, user_id):
    """Block a user"""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_staff:
        messages.error(request, 'Cannot block admin users!')
    else:
        user.is_active = False
        user.save()
        messages.success(request, f'User "{user.username}" has been blocked.')
    
    return redirect('users')


@staff_member_required
def admin_unblock_user(request, user_id):
    """Unblock a user"""
    user = get_object_or_404(User, id=user_id)
    
    user.is_active = True
    user.save()
    messages.success(request, f'User "{user.username}" has been unblocked.')
    
    return redirect('users')


@staff_member_required
def admin_delete_user(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_staff:
        messages.error(request, 'Cannot delete admin users!')
    else:
        user.delete()
        messages.success(request, f'User has been deleted successfully.')
    
    return redirect('users')
