import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useCart } from '../../contexts/CartContext';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { ShoppingCart, Heart, Star } from 'lucide-react';
import { addToWishlist } from '../../lib/api';

export const ProductCard = ({ product }) => {
  const { isAuthenticated, token } = useAuth();
  const { addToCart } = useCart();

  const handleAddToCart = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!isAuthenticated) {
      toast.error('Please login to add items to cart');
      return;
    }
    
    try {
      await addToCart(product.product_id, 1);
      toast.success('Added to cart!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add to cart');
    }
  };

  const handleAddToWishlist = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!isAuthenticated) {
      toast.error('Please login to add to wishlist');
      return;
    }
    
    try {
      await addToWishlist(product.product_id);
      toast.success('Added to wishlist!');
    } catch (error) {
      toast.error('Failed to add to wishlist');
    }
  };

  return (
    <Link 
      to={`/products/${product.product_id}`}
      className="group block"
      data-testid={`product-card-${product.product_id}`}
    >
      <div className="relative overflow-hidden rounded-xl bg-card">
        {/* Image */}
        <div className="aspect-[3/4] overflow-hidden bg-muted">
          <img
            src={product.images?.[0] || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500'}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            loading="lazy"
          />
        </div>

        {/* Quick actions */}
        <div className="absolute top-3 right-3 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <Button
            variant="secondary"
            size="icon"
            className="w-9 h-9 rounded-full shadow-lg"
            onClick={handleAddToWishlist}
            data-testid={`wishlist-btn-${product.product_id}`}
          >
            <Heart className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="w-9 h-9 rounded-full shadow-lg"
            onClick={handleAddToCart}
            data-testid={`add-to-cart-btn-${product.product_id}`}
          >
            <ShoppingCart className="w-4 h-4" />
          </Button>
        </div>

        {/* Stock badge */}
        {product.stock < 10 && product.stock > 0 && (
          <div className="absolute top-3 left-3">
            <span className="px-2 py-1 text-xs font-medium bg-accent text-accent-foreground rounded-full">
              Only {product.stock} left
            </span>
          </div>
        )}
        {product.stock === 0 && (
          <div className="absolute top-3 left-3">
            <span className="px-2 py-1 text-xs font-medium bg-destructive text-destructive-foreground rounded-full">
              Out of stock
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="mt-4 space-y-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
            <span className="text-sm font-medium">{product.rating?.toFixed(1) || '0.0'}</span>
          </div>
          <span className="text-sm text-muted-foreground">({product.review_count || 0})</span>
        </div>
        
        <h3 className="font-medium text-foreground line-clamp-2 group-hover:text-primary transition-colors">
          {product.name}
        </h3>
        
        <p className="text-lg font-bold">
          ${product.price?.toFixed(2)}
        </p>
      </div>
    </Link>
  );
};

export const ProductCardSkeleton = () => (
  <div className="animate-pulse">
    <div className="aspect-[3/4] rounded-xl bg-muted skeleton-shimmer"></div>
    <div className="mt-4 space-y-2">
      <div className="h-4 bg-muted rounded w-20"></div>
      <div className="h-5 bg-muted rounded w-full"></div>
      <div className="h-6 bg-muted rounded w-16"></div>
    </div>
  </div>
);
