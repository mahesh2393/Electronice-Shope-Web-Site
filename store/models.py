from django.db import models
from django.contrib.auth.models import User
import random
import string
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    stock = models.IntegerField(default=0)
    
    # ✅ STOCK MANAGEMENT FIELDS
    low_stock_threshold = models.IntegerField(default=5, help_text="Alert when stock falls below this number")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Stock Keeping Unit")
    is_active = models.BooleanField(default=True, help_text="Product available for sale")
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    
    # ✅ Stock tracking fields
    last_stock_update = models.DateTimeField(auto_now=True)
    stock_updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='stock_updates'
    )

    def __str__(self):
        return f"{self.name} (Stock: {self.stock})"
    
    def save(self, *args, **kwargs):
        # Generate SKU if not exists
        if not self.sku:
            cat_code = self.category.name[:3].upper() if self.category else "GEN"
            year = datetime.now().strftime('%Y')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.sku = f"{cat_code}-{year}-{random_str}"
            
            # Ensure SKU is unique
            while Product.objects.filter(sku=self.sku).exists():
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                self.sku = f"{cat_code}-{year}-{random_str}"
        
        super().save(*args, **kwargs)
    
    @property
    def is_low_stock(self):
        """Check if product is low on stock"""
        return self.stock <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        """Check if product is out of stock"""
        return self.stock <= 0
    
    @property
    def stock_status(self):
        """Get stock status text"""
        if self.stock <= 0:
            return 'Out of Stock'
        elif self.stock <= self.low_stock_threshold:
            return 'Low Stock'
        else:
            return 'In Stock'
    
    @property
    def stock_status_color(self):
        """Get stock status color"""
        if self.stock <= 0:
            return '#dc3545'  # Red
        elif self.stock <= self.low_stock_threshold:
            return '#ffc107'  # Yellow
        else:
            return '#28a745'  # Green


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class CustomProduct(models.Model):
    """Custom product requests ke liye model"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text="Product ka naam")
    description = models.TextField(help_text="Product ke baare mein details")
    size = models.CharField(max_length=50, blank=True, null=True, help_text="Size agar chahiye to")
    color = models.CharField(max_length=50, blank=True, null=True, help_text="Color preference")
    material = models.CharField(max_length=100, blank=True, null=True, help_text="Material type")
    design_instructions = models.TextField(blank=True, null=True, help_text="Khaas instructions")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Custom: {self.name} by {self.user.username}"


class Order(models.Model):
    # Order Status Choices
    ORDER_STATUS = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Mobile Wallet'),
    ]
    
    # Payment Status Choices
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    total_amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Order Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    
    # UNIQUE ORDER TRACKING NUMBER
    tracking_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    # SHORT TRACKING ID (For easy sharing)
    tracking_id = models.CharField(max_length=10, unique=True, blank=True, null=True)
    
    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Courier Details
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    courier_tracking_url = models.URLField(blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)
    
    # Notes
    admin_notes = models.TextField(blank=True, null=True)
    
    def generate_tracking_number(self):
        """Generate unique tracking number"""
        date_part = datetime.now().strftime('%Y%m%d')
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        tracking_number = f"MGS{date_part}{random_part}"
        
        while Order.objects.filter(tracking_number=tracking_number).exists():
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            tracking_number = f"MGS{date_part}{random_part}"
        
        return tracking_number
    
    def generate_tracking_id(self):
        """Generate short tracking ID for easy sharing"""
        random_num = ''.join(random.choices(string.digits, k=6))
        random_letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        tracking_id = f"{random_num}{random_letters}"
        
        while Order.objects.filter(tracking_id=tracking_id).exists():
            random_num = ''.join(random.choices(string.digits, k=6))
            random_letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            tracking_id = f"{random_num}{random_letters}"
        
        return tracking_id
    
    def save(self, *args, **kwargs):
        """Auto generate tracking number on save"""
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
        if not self.tracking_id:
            self.tracking_id = self.generate_tracking_id()
        if not self.estimated_delivery:
            self.estimated_delivery = datetime.now().date() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def get_status_display_color(self):
        """Return color based on order status"""
        colors = {
            'pending': '#ffc107',
            'confirmed': '#17a2b8',
            'processing': '#6f42c1',
            'shipped': '#007bff',
            'out_for_delivery': '#fd7e14',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        return colors.get(self.status, '#6c757d')
    
    def get_status_percentage(self):
        """Return percentage based on order status"""
        percentages = {
            'pending': 10,
            'confirmed': 25,
            'processing': 40,
            'shipped': 60,
            'out_for_delivery': 80,
            'delivered': 100,
            'cancelled': 0,
        }
        return percentages.get(self.status, 0)
    
    def __str__(self):
        return f"Order #{self.id} - {self.tracking_number}"
    
    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.IntegerField()
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this item (GETTER only)"""
        return self.quantity * self.price


class WhatsAppInquiry(models.Model):
    INQUIRY_STATUS = (
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=INQUIRY_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Inquiry from {self.name} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']


# ========== PROFILE MODEL ==========
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"
    
    class Meta:
        db_table = 'user_profile'


# ========== STOCK MANAGEMENT MODELS ==========

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('damage', 'Damage'),
        ('restock', 'Restock'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    
    def __str__(self):
        return f"{self.product.name} - {self.get_movement_type_display()} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Save the movement first
        super().save(*args, **kwargs)
        
        # Update product stock based on movement type
        if self.movement_type in ['purchase', 'return', 'restock']:
            self.product.stock += self.quantity
        elif self.movement_type in ['sale', 'damage']:
            self.product.stock -= self.quantity
        
        # Ensure stock doesn't go negative
        if self.product.stock < 0:
            self.product.stock = 0
        
        self.product.last_stock_update = timezone.now()
        self.product.stock_updated_by = self.created_by
        self.product.save()
    
    class Meta:
        ordering = ['-created_at']


# ========== SIGNALS ==========

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile when user is created"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    Profile.objects.get_or_create(user=instance)


# ✅ Signal to create stock movement when order is placed
@receiver(post_save, sender=OrderItem)
def create_stock_movement_on_order(sender, instance, created, **kwargs):
    """Create stock movement when order item is created - Auto deduct stock"""
    if created:
        # Create stock movement for sale
        StockMovement.objects.create(
            product=instance.product,
            quantity=instance.quantity,
            movement_type='sale',
            notes=f"Order #{instance.order.id} - Customer: {instance.order.name}",
            created_by=instance.order.user,
            order=instance.order
        )


# ✅ Signal to update product stock when stock movement is created (Alternative)
@receiver(post_save, sender=StockMovement)
def update_product_stock_on_movement(sender, instance, created, **kwargs):
    """Update product stock when stock movement is created"""
    if created:
        # This is already handled in StockMovement.save()
        # But kept for additional processing if needed
        pass