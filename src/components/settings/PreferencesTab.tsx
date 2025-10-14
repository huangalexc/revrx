'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Divider,
  Button,
  Switch,
  Select,
  SelectItem,
  RadioGroup,
  Radio,
} from '@heroui/react';
import {
  ChevronRight,
  CreditCard,
  Sun,
  Moon,
  Monitor,
  Save,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import Link from 'next/link';
import {
  getUserPreferences,
  updateUserPreferences,
  type UserPreferences,
} from '@/lib/api/users';

// Timezone options (common timezones)
const TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time (HT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
];

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Español (Spanish)' },
  { value: 'fr', label: 'Français (French)' },
  { value: 'de', label: 'Deutsch (German)' },
  { value: 'pt', label: 'Português (Portuguese)' },
];

export default function PreferencesTab() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Preference states
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');
  const [language, setLanguage] = useState('en');
  const [timezone, setTimezone] = useState('America/New_York');
  const [dateFormat, setDateFormat] = useState<'MM/DD/YYYY' | 'DD/MM/YYYY'>('MM/DD/YYYY');
  const [timeFormat, setTimeFormat] = useState<'12h' | '24h'>('12h');

  // Notification preferences
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [reportNotifications, setReportNotifications] = useState(true);
  const [weeklyDigest, setWeeklyDigest] = useState(false);
  const [productUpdates, setProductUpdates] = useState(true);

  // Track if preferences have changed
  const [isDirty, setIsDirty] = useState(false);

  // Define applyTheme function before it's used
  const applyTheme = (selectedTheme: 'light' | 'dark' | 'system') => {
    if (typeof window === 'undefined') return;

    let effectiveTheme: 'light' | 'dark' = 'light';

    if (selectedTheme === 'system') {
      effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
    } else {
      effectiveTheme = selectedTheme;
    }

    if (effectiveTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // Store in localStorage
    localStorage.setItem('theme', selectedTheme);
  };

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    applyTheme(newTheme);
    setIsDirty(true);
  };

  const loadPreferences = async () => {
    try {
      setIsLoading(true);
      const prefs = await getUserPreferences();

      // Get theme from localStorage (priority) or API response or default to 'system'
      const storedTheme = localStorage.getItem('theme') as 'light' | 'dark' | 'system' | null;
      const selectedTheme = storedTheme || prefs.theme || 'system';

      setTheme(selectedTheme);
      setLanguage(prefs.language || 'en');
      setTimezone(prefs.timezone || 'America/New_York');
      setDateFormat(prefs.dateFormat || 'MM/DD/YYYY');
      setTimeFormat(prefs.timeFormat || '12h');
      setEmailNotifications(prefs.emailNotifications ?? true);
      setReportNotifications(prefs.reportNotifications ?? true);
      setWeeklyDigest(prefs.weeklyDigest ?? false);
      setProductUpdates(prefs.productUpdates ?? true);

      // Apply theme to document
      applyTheme(selectedTheme);
    } catch (error: any) {
      console.error('Failed to load preferences:', error);
      setErrorMessage('Failed to load preferences');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initialize theme from localStorage immediately
    const storedTheme = localStorage.getItem('theme') as 'light' | 'dark' | 'system' | null;
    const initialTheme = storedTheme || 'system';
    setTheme(initialTheme);
    applyTheme(initialTheme);

    loadPreferences();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSavePreferences = async () => {
    try {
      setIsSaving(true);
      setSuccessMessage(null);
      setErrorMessage(null);

      await updateUserPreferences({
        theme,
        language,
        timezone,
        dateFormat,
        timeFormat,
        emailNotifications,
        reportNotifications,
        weeklyDigest,
        productUpdates,
      });

      setSuccessMessage('Preferences saved successfully!');
      setIsDirty(false);

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (error: any) {
      setErrorMessage(
        error.response?.data?.detail || 'Failed to save preferences. Please try again.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardBody className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-10 bg-gray-200 rounded"></div>
              <div className="h-10 bg-gray-200 rounded"></div>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success/Error Messages */}
      {successMessage && (
        <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-800 dark:text-green-300">{successMessage}</p>
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-800 dark:text-red-300">{errorMessage}</p>
        </div>
      )}

      {/* Display Preferences */}
      <Card>
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Display Preferences</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Customize how the application looks and feels
          </p>
        </CardHeader>
        <Divider />
        <CardBody className="p-6 space-y-6">
          {/* Theme Selection */}
          <div>
            <label className="text-sm font-medium text-gray-900 dark:text-white mb-3 block">
              Theme
            </label>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="light"
                  checked={theme === 'light'}
                  onChange={() => handleThemeChange('light')}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <Sun className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Light</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="dark"
                  checked={theme === 'dark'}
                  onChange={() => handleThemeChange('dark')}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <Moon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Dark</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="system"
                  checked={theme === 'system'}
                  onChange={() => handleThemeChange('system')}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <Monitor className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300">System</span>
              </label>
            </div>
          </div>

          {/* Timezone Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Timezone
            </label>
            <Select
              placeholder="Select your timezone"
              selectedKeys={[timezone]}
              onChange={(e) => {
                setTimezone(e.target.value);
                setIsDirty(true);
              }}
              description="Used for displaying dates and times"
              classNames={{
                value: "pl-2",
              }}
            >
              {TIMEZONES.map((tz) => (
                <SelectItem
                  key={tz.value}
                  value={tz.value}
                  classNames={{
                    base: "data-[selected=true]:pl-8",
                  }}
                >
                  {tz.label}
                </SelectItem>
              ))}
            </Select>
          </div>

          {/* Date Format */}
          <div>
            <label className="text-sm font-medium text-gray-900 dark:text-white mb-3 block">
              Date Format
            </label>
            <div className="flex gap-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  value="MM/DD/YYYY"
                  checked={dateFormat === 'MM/DD/YYYY'}
                  onChange={() => {
                    setDateFormat('MM/DD/YYYY');
                    setIsDirty(true);
                  }}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">MM/DD/YYYY (12/31/2025)</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  value="DD/MM/YYYY"
                  checked={dateFormat === 'DD/MM/YYYY'}
                  onChange={() => {
                    setDateFormat('DD/MM/YYYY');
                    setIsDirty(true);
                  }}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">DD/MM/YYYY (31/12/2025)</span>
              </label>
            </div>
          </div>

          {/* Time Format */}
          <div>
            <label className="text-sm font-medium text-gray-900 dark:text-white mb-3 block">
              Time Format
            </label>
            <div className="flex gap-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  value="12h"
                  checked={timeFormat === '12h'}
                  onChange={() => {
                    setTimeFormat('12h');
                    setIsDirty(true);
                  }}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">12-hour (2:30 PM)</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  value="24h"
                  checked={timeFormat === '24h'}
                  onChange={() => {
                    setTimeFormat('24h');
                    setIsDirty(true);
                  }}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">24-hour (14:30)</span>
              </label>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Notification Preferences */}
      <Card>
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Notifications</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Manage how you receive notifications
          </p>
        </CardHeader>
        <Divider />
        <CardBody className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Email Notifications</p>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Receive general email notifications
              </p>
            </div>
            <Switch
              isSelected={emailNotifications}
              onValueChange={(value) => {
                setEmailNotifications(value);
                setIsDirty(true);
              }}
              color="primary"
            />
          </div>

          <Divider />

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Report Ready Notifications</p>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Get notified when your encounter reports are ready
              </p>
            </div>
            <Switch
              isSelected={reportNotifications}
              onValueChange={(value) => {
                setReportNotifications(value);
                setIsDirty(true);
              }}
              color="primary"
            />
          </div>

          <Divider />

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Weekly Digest</p>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Receive a weekly summary of your encounters and revenue
              </p>
            </div>
            <Switch
              isSelected={weeklyDigest}
              onValueChange={(value) => {
                setWeeklyDigest(value);
                setIsDirty(true);
              }}
              color="primary"
            />
          </div>

          <Divider />

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Product Updates</p>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Get notified about new features and improvements
              </p>
            </div>
            <Switch
              isSelected={productUpdates}
              onValueChange={(value) => {
                setProductUpdates(value);
                setIsDirty(true);
              }}
              color="primary"
            />
          </div>
        </CardBody>
      </Card>

      {/* Save Button */}
      {isDirty && (
        <div className="flex justify-end">
          <Button
            color="primary"
            size="lg"
            isLoading={isSaving}
            isDisabled={isSaving}
            startContent={!isSaving && <Save className="w-4 h-4" />}
            onClick={handleSavePreferences}
          >
            {isSaving ? 'Saving...' : 'Save Preferences'}
          </Button>
        </div>
      )}

      {/* Billing & Subscription Section */}
      <Card>
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Billing & Subscription</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Manage your subscription, billing information, and payment methods
          </p>
        </CardHeader>
        <Divider />
        <CardBody className="p-6">
          <Link
            href="/subscription"
            className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
                <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Manage Subscription
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  View plans, billing history, and payment methods
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
          </Link>
        </CardBody>
      </Card>
    </div>
  );
}
