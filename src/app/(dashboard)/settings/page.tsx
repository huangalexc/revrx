'use client';

import { useState } from 'react';
import { Tabs, Tab } from '@heroui/react';
import { User, Settings as SettingsIcon } from 'lucide-react';
import ErrorBoundary from '@/components/ErrorBoundary';
import ProfileTab from '@/components/settings/ProfileTab';
import PreferencesTab from '@/components/settings/PreferencesTab';

function SettingsContent() {
  const [selectedTab, setSelectedTab] = useState('profile');

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Manage your account settings and preferences
        </p>
      </div>

      {/* Tab Navigation */}
      <Tabs
        selectedKey={selectedTab}
        onSelectionChange={(key) => setSelectedTab(key as string)}
        aria-label="Settings tabs"
        variant="underlined"
        classNames={{
          tabList: "gap-6 w-full relative rounded-none p-0 border-b border-gray-200",
          cursor: "w-full bg-blue-600",
          tab: "max-w-fit px-0 h-12",
          tabContent: "group-data-[selected=true]:text-blue-600"
        }}
      >
        {/* Profile Tab */}
        <Tab
          key="profile"
          title={
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4" />
              <span>Profile</span>
            </div>
          }
        >
          <div className="mt-6">
            <ProfileTab />
          </div>
        </Tab>

        {/* Preferences Tab */}
        <Tab
          key="preferences"
          title={
            <div className="flex items-center space-x-2">
              <SettingsIcon className="w-4 h-4" />
              <span>Preferences</span>
            </div>
          }
        >
          <div className="mt-6">
            <PreferencesTab />
          </div>
        </Tab>
      </Tabs>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ErrorBoundary>
      <SettingsContent />
    </ErrorBoundary>
  );
}
