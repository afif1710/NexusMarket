import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { getSellerProducts, getSellerStats, createProduct, updateProduct, deleteProduct, getCategories, getOrders } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  LayoutDashboard, Package, ShoppingCart, Plus, 
  DollarSign, Boxes, Edit, Trash2 
} from 'lucide-react';

const SellerDashboard = () => {
  const location = useLocation();
  
  const navItems = [
    { path: '/seller', label: 'Overview', icon: LayoutDashboard },
    { path: '/seller/products', label: 'My Products', icon: Package },
    { path: '/seller/orders', label: 'Orders', icon: ShoppingCart },
  ];

  return (
    <div className="min-h-screen py-8" data-testid="seller-dashboard">
      <div className="container mx-auto px-4">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <aside className="lg:w-64 shrink-0">
            <div className="sticky top-24">
              <h1 className="text-2xl font-bold mb-6">Seller Dashboard</h1>
              <nav className="space-y-1">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      location.pathname === item.path
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </aside>

          {/* Content */}
          <main className="flex-1 min-w-0">
            <Routes>
              <Route index element={<SellerOverview />} />
              <Route path="products" element={<SellerProducts />} />
              <Route path="orders" element={<SellerOrders />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
};

const SellerOverview = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await getSellerStats();
        setStats(res.data);
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) return <div>Loading...</div>;

  const statCards = [
    { title: 'Total Sales', value: `$${stats?.total_sales?.toFixed(2) || 0}`, icon: DollarSign },
    { title: 'Total Orders', value: stats?.total_orders || 0, icon: ShoppingCart },
    { title: 'Total Products', value: stats?.total_products || 0, icon: Package },
    { title: 'Total Stock', value: stats?.total_stock || 0, icon: Boxes },
  ];

  return (
    <div className="space-y-8" data-testid="seller-overview">
      <h2 className="text-2xl font-bold">Overview</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="w-5 h-5 text-primary" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

const SellerProducts = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editProduct, setEditProduct] = useState(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    category_id: '',
    stock: '',
    images: [''],
    tags: ''
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          getSellerProducts(),
          getCategories()
        ]);
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleOpenDialog = (product = null) => {
    if (product) {
      setEditProduct(product);
      setForm({
        name: product.name,
        description: product.description,
        price: product.price.toString(),
        category_id: product.category_id,
        stock: product.stock.toString(),
        images: product.images?.length ? product.images : [''],
        tags: product.tags?.join(', ') || ''
      });
    } else {
      setEditProduct(null);
      setForm({
        name: '',
        description: '',
        price: '',
        category_id: '',
        stock: '',
        images: [''],
        tags: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const productData = {
      name: form.name,
      description: form.description,
      price: parseFloat(form.price),
      category_id: form.category_id,
      stock: parseInt(form.stock),
      images: form.images.filter(img => img.trim()),
      tags: form.tags.split(',').map(t => t.trim().toLowerCase()).filter(t => t)
    };

    try {
      if (editProduct) {
        await updateProduct(editProduct.product_id, productData);
        setProducts(products.map(p => 
          p.product_id === editProduct.product_id ? { ...p, ...productData } : p
        ));
        toast.success('Product updated');
      } else {
        const res = await createProduct(productData);
        setProducts([res.data, ...products]);
        toast.success('Product created');
      }
      setDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save product');
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    
    try {
      await deleteProduct(productId);
      setProducts(products.filter(p => p.product_id !== productId));
      toast.success('Product deleted');
    } catch (error) {
      toast.error('Failed to delete product');
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div data-testid="seller-products">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">My Products</h2>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} className="rounded-full" data-testid="add-product-btn">
              <Plus className="w-4 h-4 mr-2" /> Add Product
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editProduct ? 'Edit Product' : 'Add Product'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">Product Name</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="price">Price ($)</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    value={form.price}
                    onChange={(e) => setForm({ ...form, price: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="stock">Stock</Label>
                  <Input
                    id="stock"
                    type="number"
                    value={form.stock}
                    onChange={(e) => setForm({ ...form, stock: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="category">Category</Label>
                <Select value={form.category_id} onValueChange={(v) => setForm({ ...form, category_id: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.category_id} value={cat.category_id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="images">Image URL</Label>
                <Input
                  id="images"
                  value={form.images[0]}
                  onChange={(e) => setForm({ ...form, images: [e.target.value] })}
                  placeholder="https://..."
                />
              </div>
              <div>
                <Label htmlFor="tags">Tags (comma separated)</Label>
                <Input
                  id="tags"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  placeholder="electronics, wireless, audio"
                />
              </div>
              <Button type="submit" className="w-full rounded-full">
                {editProduct ? 'Update Product' : 'Create Product'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {products.length === 0 ? (
        <div className="text-center py-16">
          <Package className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">No products yet. Add your first product!</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {products.map((product) => (
            <div key={product.product_id} className="flex items-center gap-4 p-4 rounded-xl bg-card border border-border">
              <img
                src={product.images?.[0] || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=100'}
                alt={product.name}
                className="w-20 h-20 rounded-lg object-cover"
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{product.name}</p>
                <p className="text-lg font-bold">${product.price?.toFixed(2)}</p>
                <p className="text-sm text-muted-foreground">Stock: {product.stock}</p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => handleOpenDialog(product)}
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDelete(product.product_id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const SellerOrders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const res = await getOrders();
        setOrders(res.data);
      } catch (error) {
        console.error('Error fetching orders:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchOrders();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div data-testid="seller-orders">
      <h2 className="text-2xl font-bold mb-6">Orders</h2>
      {orders.length === 0 ? (
        <div className="text-center py-16">
          <ShoppingCart className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">No orders yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <div key={order.order_id} className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center justify-between mb-2">
                <p className="font-medium">{order.order_id}</p>
                <p className="font-bold">${order.total?.toFixed(2)}</p>
              </div>
              <p className="text-sm text-muted-foreground mb-2">
                {new Date(order.created_at).toLocaleDateString()}
              </p>
              <div className="flex flex-wrap gap-2">
                {order.items?.map((item, idx) => (
                  <span key={idx} className="text-xs px-2 py-1 bg-muted rounded">
                    {item.product_name} x{item.quantity}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SellerDashboard;
