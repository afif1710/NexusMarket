import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Products
export const getProducts = (params) => api.get('/products', { params });
export const getProduct = (id) => api.get(`/products/${id}`);
export const createProduct = (data) => api.post('/products', data);
export const updateProduct = (id, data) => api.put(`/products/${id}`, data);
export const deleteProduct = (id) => api.delete(`/products/${id}`);

// Categories
export const getCategories = () => api.get('/categories');

// Cart
export const getCart = () => api.get('/cart');
export const addToCart = (productId, quantity) => api.post('/cart/add', { product_id: productId, quantity });
export const updateCart = (items) => api.put('/cart/update', { items });
export const removeFromCart = (productId) => api.delete(`/cart/item/${productId}`);
export const clearCart = () => api.delete('/cart');

// Wishlist
export const getWishlist = () => api.get('/wishlist');
export const addToWishlist = (productId) => api.post(`/wishlist/${productId}`);
export const removeFromWishlist = (productId) => api.delete(`/wishlist/${productId}`);

// Reviews
export const getProductReviews = (productId) => api.get(`/products/${productId}/reviews`);
export const createReview = (data) => api.post('/reviews', data);

// Orders
export const getOrders = () => api.get('/orders');
export const getOrder = (id) => api.get(`/orders/${id}`);
export const createOrder = (data) => api.post('/orders', data);
export const updateOrderStatus = (id, status) => api.put(`/orders/${id}/status`, null, { params: { status } });

// Payments
export const createStripeSession = (orderId, originUrl) => 
  api.post('/payments/stripe/create-session', { order_id: orderId, origin_url: originUrl });
export const getPaymentStatus = (sessionId) => api.get(`/payments/status/${sessionId}`);

// Recommendations
export const getRecommendations = () => api.get('/recommendations');
export const getAIRecommendations = (productId) => api.get(`/recommendations/ai/${productId}`);

// Newsletter
export const subscribeNewsletter = (email) => api.post('/newsletter/subscribe', { email });

// Admin
export const getAdminStats = () => api.get('/admin/stats');
export const getAdminUsers = () => api.get('/admin/users');
export const updateUserRole = (userId, role) => api.put(`/admin/users/${userId}/role`, null, { params: { role } });

// Seller
export const getSellerProducts = () => api.get('/seller/products');
export const getSellerStats = () => api.get('/seller/stats');

// Seed
export const seedData = () => api.post('/seed');

export default api;
