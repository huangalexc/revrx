'use client';

import { useEffect, useState } from 'react';
import { Clock, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

interface TrialCountdownProps {
  trialEndDate: string;
  className?: string;
}

export function TrialCountdown({ trialEndDate, className = '' }: TrialCountdownProps) {
  const router = useRouter();
  const [daysRemaining, setDaysRemaining] = useState(0);

  useEffect(() => {
    const calculateDaysRemaining = () => {
      const now = new Date();
      const endDate = new Date(trialEndDate);
      const diffTime = endDate.getTime() - now.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      setDaysRemaining(Math.max(0, diffDays));
    };

    calculateDaysRemaining();
    const interval = setInterval(calculateDaysRemaining, 1000 * 60 * 60); // Update every hour

    return () => clearInterval(interval);
  }, [trialEndDate]);

  if (daysRemaining === 0) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>Your trial has expired. Subscribe to continue using the service.</span>
          <Button
            size="sm"
            onClick={() => router.push('/subscription')}
          >
            Subscribe Now
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (daysRemaining <= 3) {
    return (
      <Alert variant="warning" className={className}>
        <Clock className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>Your trial expires in {daysRemaining} day{daysRemaining !== 1 ? 's' : ''}.</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => router.push('/subscription')}
          >
            Subscribe Now
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={`flex items-center gap-2 text-sm text-muted-foreground ${className}`}>
      <Clock className="h-4 w-4" />
      <span>{daysRemaining} days remaining in trial</span>
    </div>
  );
}
