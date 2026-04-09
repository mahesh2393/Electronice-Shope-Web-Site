from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Category, Brand, Product, Cart, Order, OrderItem
from .serializers import (
    UserSerializer, CategorySerializer, BrandSerializer, ProductSerializer,
    CartSerializer, OrderSerializer, RegisterSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """Category API"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['name']


class BrandViewSet(viewsets.ModelViewSet):
    """Brand API"""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    search_fields = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    """Product API"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'description']
    filterset_fields = ['category', 'brand']
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products (first 10)"""
        products = Product.objects.all()[:10]
        serializer = self.get_serializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    """Cart API"""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add item to cart"""
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id)
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear cart"""
        Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'Cart cleared'}, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    """Order API"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        """Create order from cart"""
        cart_items = Cart.objects.filter(user=request.user)
        
        if not cart_items:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate total
        total = sum(item.product.price * item.quantity for item in cart_items)
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            name=request.data.get('name'),
            email=request.data.get('email'),
            phone=request.data.get('phone'),
            address=request.data.get('address'),
            city=request.data.get('city'),
            pincode=request.data.get('pincode'),
            total_amount=total,
            payment_method=request.data.get('payment_method', 'cod')
        )
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        # Clear cart
        cart_items.delete()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Track order"""
        order = self.get_object()
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    """User Registration API"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """User Profile API"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user