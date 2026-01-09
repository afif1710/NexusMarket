import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { getPaymentStatus, getOrder } from '../lib/api';
import { useCart } from '../contexts/CartContext';
import { Button } from '../components/ui/button';
import { CheckCircle, XCircle, Loader2, Package } from 'lucide-react';

const OrderSuccessPage = () => {
  const [searchParams] = useSearchParams();
  const { clearCart } = useCart();
  const [status, setStatus] = useState('loading');
  const [order, setOrder] = useState(null);
  const [pollCount, setPollCount] = useState(0);

  const sessionId = searchParams.get('session_id');
  const orderId = searchParams.get('order_id');

  useEffect(() => {
    const checkPayment = async () => {
      if (!sessionId && !orderId) {
        setStatus('error');
        return;
      }

      try {
        if (sessionId) {
          // Poll Stripe payment status
          const res = await getPaymentStatus(sessionId);
          
          if (res.data.payment_status === 'paid') {
            setStatus('success');
            await clearCart();
            
            // Get order details
            if (res.data.order_id) {
              const orderRes = await getOrder(res.data.order_id);
              setOrder(orderRes.data);
            }
          } else if (res.data.status === 'expired') {
            setStatus('error');
          } else if (pollCount < 5) {
            // Continue polling
            setTimeout(() => setPollCount(prev => prev + 1), 2000);
          } else {
            setStatus('pending');
          }
        } else if (orderId) {
          // Direct order (e.g., PayPal)
          const orderRes = await getOrder(orderId);
          setOrder(orderRes.data);
          setStatus('success');
          await clearCart();
        }
      } catch (error) {
        console.error('Error checking payment:', error);
        if (pollCount < 3) {
          setTimeout(() => setPollCount(prev => prev + 1), 2000);
        } else {
          setStatus('error');
        }
      }
    };

    if (status === 'loading' || pollCount > 0) {
      checkPayment();
    }
  }, [sessionId, orderId, pollCount, status, clearCart]);

  return (
    <div className="min-h-screen py-16" data-testid="order-success-page">
      <div className="container mx-auto px-4 max-w-lg text-center">
        {status === 'loading' && (
          <div className="animate-fade-in">
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-primary animate-spin" />
            <h1 className="text-2xl font-bold mb-2">Processing Payment...</h1>
            <p className="text-muted-foreground">Please wait while we confirm your payment.</p>
          </div>
        )}

        {status === 'success' && (
          <div className="animate-scale-in">
            <CheckCircle className="w-20 h-20 mx-auto mb-6 text-green-500" />
            <h1 className="text-3xl font-bold mb-2">Order Confirmed!</h1>
            <p className="text-muted-foreground mb-8">
              Thank you for your purchase. Your order has been placed successfully.
            </p>

            {order && (
              <div className="text-left bg-card border border-border rounded-xl p-6 mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-semibold">Order Details</h2>
                  <span className="text-sm text-muted-foreground">
                    {order.order_id}
                  </span>
                </div>
                
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Items</span>
                    <span>{order.items?.length || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span>${order.subtotal?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Shipping</span>
                    <span>${order.shipping?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tax</span>
                    <span>${order.tax?.toFixed(2)}</span>
                  </div>
                  <div className="border-t border-border pt-2">
                    <div className="flex justify-between font-bold">
                      <span>Total</span>
                      <span>${order.total?.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 rounded-lg bg-muted">
                  <p className="text-sm">
                    <span className="font-medium">Shipping to:</span>
                    <br />
                    {order.shipping_address?.name}
                    <br />
                    {order.shipping_address?.address}, {order.shipping_address?.city}
                    <br />
                    {order.shipping_address?.state} {order.shipping_address?.zip}
                  </p>
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild className="rounded-full">
                <Link to="/orders">
                  <Package className="w-4 h-4 mr-2" /> View Orders
                </Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full">
                <Link to="/products">Continue Shopping</Link>
              </Button>
            </div>
          </div>
        )}

        {status === 'pending' && (
          <div className="animate-fade-in">
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
            <h1 className="text-2xl font-bold mb-2">Payment Pending</h1>
            <p className="text-muted-foreground mb-8">
              Your payment is being processed. Please check your email for confirmation.
            </p>
            <Button asChild className="rounded-full">
              <Link to="/orders">View Orders</Link>
            </Button>
          </div>
        )}

        {status === 'error' && (
          <div className="animate-fade-in">
            <XCircle className="w-20 h-20 mx-auto mb-6 text-destructive" />
            <h1 className="text-3xl font-bold mb-2">Payment Failed</h1>
            <p className="text-muted-foreground mb-8">
              Something went wrong with your payment. Please try again.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild className="rounded-full">
                <Link to="/checkout">Try Again</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-full">
                <Link to="/cart">Back to Cart</Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrderSuccessPage;
