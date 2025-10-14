'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Card,
  CardBody,
  CardHeader,
  Input,
  Button,
  Divider,
  Progress,
  Select,
  SelectItem,
} from '@heroui/react';
import { Save, Lock, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';
import {
  profileUpdateSchema,
  passwordChangeSchema,
  calculatePasswordStrength,
  type ProfileUpdateFormData,
  type PasswordChangeFormData,
} from '@/lib/schemas/profile';
import {
  getUserProfile,
  updateUserProfile,
  changePassword,
  type UserProfile,
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

export default function ProfileTab() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [passwordSuccessMessage, setPasswordSuccessMessage] = useState<string | null>(null);
  const [passwordErrorMessage, setPasswordErrorMessage] = useState<string | null>(null);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleSubmitProfile,
    formState: { errors: profileErrors, isDirty: isProfileDirty },
    reset: resetProfile,
    watch: watchProfile,
  } = useForm<ProfileUpdateFormData>({
    resolver: zodResolver(profileUpdateSchema),
  });

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    formState: { errors: passwordErrors },
    reset: resetPassword,
    watch: watchPassword,
  } = useForm<PasswordChangeFormData>({
    resolver: zodResolver(passwordChangeSchema),
  });

  const newPassword = watchPassword('newPassword');
  const passwordStrength = calculatePasswordStrength(newPassword || '');

  // Load user profile
  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      setIsLoading(true);
      const profile = await getUserProfile();
      setUserProfile(profile);
      resetProfile({
        name: profile.name || '',
        email: profile.email,
        phone: profile.phone || '',
        timezone: profile.timezone || '',
        language: profile.language || 'en',
      });
    } catch (error: any) {
      setErrorMessage(error.response?.data?.detail || 'Failed to load profile');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle profile update
  const onSubmitProfile = async (data: ProfileUpdateFormData) => {
    try {
      setIsSaving(true);
      setSuccessMessage(null);
      setErrorMessage(null);

      await updateUserProfile(data);

      setSuccessMessage('Profile updated successfully!');

      // Reload profile to get latest data
      await loadUserProfile();

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (error: any) {
      setErrorMessage(
        error.response?.data?.detail || 'Failed to update profile. Please try again.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  // Handle password change
  const onSubmitPassword = async (data: PasswordChangeFormData) => {
    try {
      setIsChangingPassword(true);
      setPasswordSuccessMessage(null);
      setPasswordErrorMessage(null);

      await changePassword({
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
      });

      setPasswordSuccessMessage('Password changed successfully!');
      resetPassword();

      // Clear success message after 5 seconds
      setTimeout(() => setPasswordSuccessMessage(null), 5000);
    } catch (error: any) {
      setPasswordErrorMessage(
        error.response?.data?.detail || 'Failed to change password. Please check your current password.'
      );
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardBody className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Profile Information Section */}
      <Card>
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Profile Information</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Update your personal information and contact details
          </p>
        </CardHeader>
        <Divider />
        <CardBody className="p-6">
          <form onSubmit={handleSubmitProfile(onSubmitProfile)} className="space-y-6">
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

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Full Name
              </label>
              <Input
                placeholder="Enter your full name"
                {...registerProfile('name')}
                isInvalid={!!profileErrors.name}
                errorMessage={profileErrors.name?.message}
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="your.email@example.com"
                {...registerProfile('email')}
                isInvalid={!!profileErrors.email}
                errorMessage={profileErrors.email?.message}
                description="You'll need to verify a new email address"
              />
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Phone Number
              </label>
              <Input
                type="tel"
                placeholder="+1234567890"
                {...registerProfile('phone')}
                isInvalid={!!profileErrors.phone}
                errorMessage={profileErrors.phone?.message}
                description="Optional. Include country code (e.g., +1 for US)"
              />
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button
                type="submit"
                color="primary"
                isLoading={isSaving}
                isDisabled={!isProfileDirty || isSaving}
                startContent={!isSaving && <Save className="w-4 h-4" />}
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {/* Password Change Section */}
      <Card>
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Change Password</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Update your password to keep your account secure
          </p>
        </CardHeader>
        <Divider />
        <CardBody className="p-6">
          <form onSubmit={handleSubmitPassword(onSubmitPassword)} className="space-y-6">
            {/* Success/Error Messages */}
            {passwordSuccessMessage && (
              <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <p className="text-sm text-green-800 dark:text-green-300">{passwordSuccessMessage}</p>
              </div>
            )}

            {passwordErrorMessage && (
              <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                <p className="text-sm text-red-800 dark:text-red-300">{passwordErrorMessage}</p>
              </div>
            )}

            {/* Current Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Current Password
              </label>
              <Input
                type={showCurrentPassword ? 'text' : 'password'}
                placeholder="Enter your current password"
                {...registerPassword('currentPassword')}
                isInvalid={!!passwordErrors.currentPassword}
                errorMessage={passwordErrors.currentPassword?.message}
                endContent={
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="focus:outline-none"
                  >
                    {showCurrentPassword ? (
                      <EyeOff className="w-4 h-4 text-gray-400" />
                    ) : (
                      <Eye className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                }
              />
            </div>

            {/* New Password */}
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  New Password
                </label>
                <Input
                  type={showNewPassword ? 'text' : 'password'}
                  placeholder="Enter your new password"
                  {...registerPassword('newPassword')}
                  isInvalid={!!passwordErrors.newPassword}
                  errorMessage={passwordErrors.newPassword?.message}
                  endContent={
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="focus:outline-none"
                    >
                      {showNewPassword ? (
                        <EyeOff className="w-4 h-4 text-gray-400" />
                      ) : (
                        <Eye className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  }
                />
              </div>

              {/* Password Strength Indicator */}
              {newPassword && (
                <div className="space-y-2">
                  <Progress
                    value={passwordStrength.score}
                    color={passwordStrength.color as any}
                    size="sm"
                    className="max-w-full"
                  />
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Password strength: <span className="font-medium">{passwordStrength.label}</span>
                  </p>
                </div>
              )}

              {/* Password Requirements */}
              <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <p>Password must contain:</p>
                <ul className="list-disc list-inside space-y-0.5 ml-2">
                  <li>At least 8 characters</li>
                  <li>One uppercase letter</li>
                  <li>One lowercase letter</li>
                  <li>One number</li>
                  <li>One special character</li>
                </ul>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Confirm New Password
              </label>
              <Input
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="Confirm your new password"
                {...registerPassword('confirmPassword')}
                isInvalid={!!passwordErrors.confirmPassword}
                errorMessage={passwordErrors.confirmPassword?.message}
                endContent={
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="focus:outline-none"
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="w-4 h-4 text-gray-400" />
                    ) : (
                      <Eye className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                }
              />
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button
                type="submit"
                color="primary"
                isLoading={isChangingPassword}
                isDisabled={isChangingPassword}
                startContent={!isChangingPassword && <Lock className="w-4 h-4" />}
              >
                {isChangingPassword ? 'Changing Password...' : 'Change Password'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
