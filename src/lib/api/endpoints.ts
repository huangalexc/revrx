export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: '/v1/auth/register',
    LOGIN: '/v1/auth/login',
    VERIFY: '/v1/auth/verify-email',
    FORGOT_PASSWORD: '/v1/auth/forgot-password',
    RESET_PASSWORD: '/v1/auth/reset-password',
    REFRESH_TOKEN: '/v1/auth/refresh',
    LOGOUT: '/v1/auth/logout',
  },
  USER: {
    ME: '/v1/users/me',
    UPDATE_PROFILE: '/v1/users/me',
    CHANGE_PASSWORD: '/v1/users/me/change-password',
    PREFERENCES: '/v1/users/me/preferences',
  },
  ENCOUNTERS: {
    LIST: '/v1/encounters',
    DETAIL: (id: string) => `/v1/encounters/${id}`,
    UPLOAD_NOTE: '/v1/encounters/upload-note',
    UPLOAD_CODES: (id: string) => `/v1/encounters/${id}/upload-codes`,
    BULK_DELETE: '/v1/encounters/bulk-delete',
    CHECK_DUPLICATE: '/v1/encounters/check-duplicate',
    BATCH_STATUS: (batchId: string) => `/v1/encounters/batch/${batchId}/status`,
  },
  REPORTS: {
    DETAIL: (id: string) => `/v1/reports/encounters/${id}`,
    SUMMARY: '/v1/reports/summary',
    CODE_CATEGORIES: '/v1/reports/summary/code-categories',
    EXPORT: (id: string, format: string) => `/v1/reports/encounters/${id}?format=${format}`,
  },
  SUBSCRIPTION: {
    START_TRIAL: '/subscriptions/start-trial',
    CANCEL: '/subscriptions/cancel',
    STATUS: '/subscriptions/status',
  },
  ADMIN: {
    USERS: '/admin/users',
    AUDIT_LOGS: '/admin/audit-logs',
    METRICS: '/admin/metrics',
  },
} as const;
