'use client';

import { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, XCircle, Clock, CreditCard, Download } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/lib/api/client';

interface SubscriptionStatus {
  is_subscribed: boolean;
  subscription_status: string;
  trial_end_date?: string;
  days_remaining?: number;
  subscription?: {
    id: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
    amount: number;
    currency: string;
    billing_interval: string;
  };
}

interface Invoice {
  id: string;
  number: string;
  status: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  invoice_pdf?: string;
  hosted_invoice_url?: string;
  created: string;
}

interface PaymentMethod {
  id: string;
  type: string;
  card: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  };
}

export default function SubscriptionPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      setLoading(true);

      // Fetch subscription status
      const statusRes = await apiClient.get('/v1/subscriptions/status');
      setStatus(statusRes.data);

      // Fetch billing history
      try {
        const billingRes = await apiClient.get('/v1/subscriptions/billing-history');
        setInvoices(billingRes.data.invoices || []);
        setPaymentMethods(billingRes.data.payment_methods || []);
      } catch (billingErr) {
        // Billing history might not exist yet, that's ok
        console.log('No billing history yet');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load subscription data';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleActivateTrial = async () => {
    try {
      setActionLoading(true);
      setError('');

      await apiClient.post('/v1/subscriptions/activate-trial', { trial_days: 7 });
      await fetchSubscriptionData();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to activate trial';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubscribe = async () => {
    try {
      setActionLoading(true);
      setError('');

      const res = await apiClient.post('/v1/subscriptions/create-checkout-session', {
        success_url: `${window.location.origin}/subscription?success=true`,
        cancel_url: `${window.location.origin}/subscription?cancelled=true`,
      });

      window.location.href = res.data.url;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create checkout session';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      setActionLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? It will remain active until the end of the billing period.')) {
      return;
    }

    try {
      setActionLoading(true);
      setError('');

      await apiClient.post('/v1/subscriptions/cancel', { cancel_at_period_end: true });
      await fetchSubscriptionData();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to cancel subscription';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      setActionLoading(true);
      setError('');

      await apiClient.post('/v1/subscriptions/reactivate');
      await fetchSubscriptionData();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to reactivate subscription';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdatePaymentMethod = async () => {
    try {
      setActionLoading(true);
      setError('');

      const res = await apiClient.post('/v1/subscriptions/create-payment-method-session', {
        success_url: `${window.location.origin}/subscription?payment_updated=true`,
        cancel_url: `${window.location.origin}/subscription`,
      });

      window.location.href = res.data.url;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create payment method session';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      setActionLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (!status) return null;

    const statusConfig: Record<string, { label: string; className: string }> = {
      TRIAL: { label: 'Trial', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
      ACTIVE: { label: 'Active', className: 'bg-green-100 text-green-800 border-green-200' },
      INACTIVE: { label: 'Inactive', className: 'bg-gray-100 text-gray-800 border-gray-200' },
      CANCELLED: { label: 'Cancelled', className: 'bg-red-100 text-red-800 border-red-200' },
      EXPIRED: { label: 'Expired', className: 'bg-red-100 text-red-800 border-red-200' },
      SUSPENDED: { label: 'Suspended', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
    };

    const config = statusConfig[status.subscription_status] || { label: status.subscription_status, className: 'bg-gray-100 text-gray-800 border-gray-200' };

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${config.className}`}>
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container max-w-6xl py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Subscription & Billing</h1>
        <p className="text-muted-foreground mt-2">Manage your subscription and billing information</p>
        <div className="mt-3">
          <a
            href="/settings"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700"
          >
            <svg
              className="mr-1 w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Settings
          </a>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Subscription Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold">Subscription Status</h2>
            {getStatusBadge()}
          </div>
        </CardHeader>
        <CardContent>
          {status && (
            <div className="space-y-4">
              {status.subscription_status === 'TRIAL' && status.days_remaining !== undefined && (
                <div className="flex items-center gap-2 p-4 bg-warning/10 rounded-lg">
                  <Clock className="w-5 h-5 text-warning" />
                  <span className="font-medium">
                    {status.days_remaining} days remaining in trial
                  </span>
                </div>
              )}

              {status.subscription && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Plan</p>
                    <p className="text-lg font-semibold">
                      ${status.subscription.amount} / {status.subscription.billing_interval}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Next Billing Date</p>
                    <p className="text-lg font-semibold">
                      {new Date(status.subscription.current_period_end).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              )}

              {status.subscription?.cancel_at_period_end && (
                <Alert>
                  <AlertDescription>
                    Your subscription will be cancelled on {new Date(status.subscription.current_period_end).toLocaleDateString()}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex gap-2">
          {status?.subscription_status === 'INACTIVE' && (
            <>
              <Button
                onClick={handleActivateTrial}
                disabled={actionLoading}
                variant="outline"
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Start 7-Day Trial
              </Button>
              <Button onClick={handleSubscribe} disabled={actionLoading}>
                Subscribe Now
              </Button>
            </>
          )}

          {status?.subscription_status === 'TRIAL' && (
            <Button onClick={handleSubscribe} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Subscribe Now
            </Button>
          )}

          {status?.subscription_status === 'ACTIVE' && !status.subscription?.cancel_at_period_end && (
            <Button
              onClick={handleCancelSubscription}
              disabled={actionLoading}
              variant="destructive"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Cancel Subscription
            </Button>
          )}

          {status?.subscription?.cancel_at_period_end && (
            <Button
              onClick={handleReactivateSubscription}
              disabled={actionLoading}
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Reactivate Subscription
            </Button>
          )}
        </CardFooter>
      </Card>

      {/* Payment Methods Card */}
      {paymentMethods.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">Payment Methods</h2>
              <Button
                onClick={handleUpdatePaymentMethod}
                disabled={actionLoading}
                variant="outline"
                size="sm"
              >
                <CreditCard className="w-4 h-4 mr-2" />
                Update Payment Method
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {paymentMethods.map((pm) => (
                <div key={pm.id} className="flex items-center gap-3 p-3 border rounded-lg">
                  <CreditCard className="w-5 h-5" />
                  <div className="flex-1">
                    <p className="font-medium capitalize">{pm.card.brand} •••• {pm.card.last4}</p>
                    <p className="text-sm text-muted-foreground">
                      Expires {pm.card.exp_month}/{pm.card.exp_year}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Billing History Card */}
      {invoices.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-2xl font-semibold">Billing History</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {invoices.map((invoice) => (
                <div key={invoice.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium">{invoice.number || invoice.id}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(invoice.created).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="font-semibold">
                        ${invoice.amount_paid.toFixed(2)} {invoice.currency.toUpperCase()}
                      </p>
                      <p className="text-sm text-muted-foreground capitalize">{invoice.status}</p>
                    </div>
                    {invoice.invoice_pdf && (
                      <Button
                        variant="ghost"
                        size="sm"
                        as="a"
                        href={invoice.invoice_pdf}
                        target="_blank"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
