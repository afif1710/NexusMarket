import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CartContext = createContext(null);

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

export const CartProvider = ({ children }) => {
  const { token, isAuthenticated } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchCart = useCallback(async () => {
    if (!isAuthenticated || !token) {
      setItems([]);
      setTotal(0);
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/cart`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setItems(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching cart:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, token]);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  const addToCart = async (productId, quantity = 1) => {
    if (!token) throw new Error('Please login to add items to cart');
    
    await axios.post(
      `${API}/cart/add`,
      { product_id: productId, quantity },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    await fetchCart();
  };

  const updateQuantity = async (productId, quantity) => {
    if (!token) return;
    
    const updatedItems = items.map(item => 
      item.product_id === productId 
        ? { product_id: item.product_id, quantity } 
        : { product_id: item.product_id, quantity: item.quantity }
    ).filter(item => item.quantity > 0);

    await axios.put(
      `${API}/cart/update`,
      { items: updatedItems },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    await fetchCart();
  };

  const removeFromCart = async (productId) => {
    if (!token) return;
    
    await axios.delete(`${API}/cart/item/${productId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    await fetchCart();
  };

  const clearCart = async () => {
    if (!token) return;
    
    await axios.delete(`${API}/cart`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    setItems([]);
    setTotal(0);
  };

  const itemCount = items.reduce((acc, item) => acc + item.quantity, 0);

  const value = {
    items,
    total,
    loading,
    itemCount,
    addToCart,
    updateQuantity,
    removeFromCart,
    clearCart,
    fetchCart
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
};
