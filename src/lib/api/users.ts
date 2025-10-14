import apiClient from './client';
import { API_ENDPOINTS } from './endpoints';

// Types
export interface UserProfile {
  id: string;
  email: string;
  name?: string;
  phone?: string;
  timezone?: string;
  language?: string;
  role: string;
  emailVerified: boolean;
  profileComplete: boolean;
  subscriptionStatus: string;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateProfileData {
  name?: string;
  email?: string;
  phone?: string;
  timezone?: string;
  language?: string;
}

export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
}

export interface UserPreferences {
  theme?: 'light' | 'dark' | 'system';
  emailNotifications?: boolean;
  reportNotifications?: boolean;
  weeklyDigest?: boolean;
  productUpdates?: boolean;
  language?: string;
  timezone?: string;
  dateFormat?: 'MM/DD/YYYY' | 'DD/MM/YYYY';
  timeFormat?: '12h' | '24h';
}

// API Functions

/**
 * Get current user profile
 */
export async function getUserProfile(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>(API_ENDPOINTS.USER.ME);
  return response.data;
}

/**
 * Update user profile
 */
export async function updateUserProfile(data: UpdateProfileData): Promise<UserProfile> {
  const response = await apiClient.patch<UserProfile>(
    API_ENDPOINTS.USER.UPDATE_PROFILE,
    data
  );
  return response.data;
}

/**
 * Change user password
 */
export async function changePassword(data: ChangePasswordData): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    API_ENDPOINTS.USER.CHANGE_PASSWORD,
    data
  );
  return response.data;
}

/**
 * Get user preferences
 */
export async function getUserPreferences(): Promise<UserPreferences> {
  const response = await apiClient.get<UserPreferences>(
    API_ENDPOINTS.USER.PREFERENCES
  );
  return response.data;
}

/**
 * Update user preferences
 */
export async function updateUserPreferences(
  data: Partial<UserPreferences>
): Promise<UserPreferences> {
  const response = await apiClient.patch<UserPreferences>(
    API_ENDPOINTS.USER.PREFERENCES,
    data
  );
  return response.data;
}
