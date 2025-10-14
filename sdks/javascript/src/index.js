/**
 * RevRx JavaScript SDK
 * Official JavaScript/Node.js client for the Post-Facto Coding Review API
 */

const axios = require('axios');

/**
 * Custom error classes
 */
class RevRxError extends Error {
  constructor(message, statusCode = null, response = null) {
    super(message);
    this.name = 'RevRxError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

class AuthenticationError extends RevRxError {
  constructor(message) {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

class RateLimitError extends RevRxError {
  constructor(message, retryAfter, limit, remaining, reset) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    this.limit = limit;
    this.remaining = remaining;
    this.reset = reset;
  }
}

class ValidationError extends RevRxError {
  constructor(message, response) {
    super(message, 422, response);
    this.name = 'ValidationError';
  }
}

class NotFoundError extends RevRxError {
  constructor(message) {
    super(message, 404);
    this.name = 'NotFoundError';
  }
}

/**
 * RevRx API Client
 */
class RevRxClient {
  /**
   * Initialize RevRx client
   * @param {Object} options - Configuration options
   * @param {string} options.apiKey - Your RevRx API key
   * @param {string} [options.baseUrl] - API base URL
   * @param {number} [options.timeout] - Request timeout in milliseconds
   */
  constructor({ apiKey, baseUrl = 'https://api.revrx.com/api/v1', timeout = 30000 }) {
    if (!apiKey) {
      throw new Error('API key is required');
    }

    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = timeout;

    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'RevRx-JavaScript-SDK/0.1.0',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          const { status, data, headers } = error.response;

          // Rate limiting
          if (status === 429) {
            throw new RateLimitError(
              'Rate limit exceeded',
              headers['retry-after'],
              headers['x-ratelimit-limit'],
              headers['x-ratelimit-remaining'],
              headers['x-ratelimit-reset']
            );
          }

          // Authentication
          if (status === 401) {
            throw new AuthenticationError('Authentication failed. Check your API key.');
          }

          // Not found
          if (status === 404) {
            throw new NotFoundError(data.detail || 'Resource not found');
          }

          // Validation
          if (status === 422) {
            throw new ValidationError(data.detail || 'Validation error', data);
          }

          // Server error
          if (status >= 500) {
            throw new RevRxError(`Server error: ${status}`, status);
          }

          // Other client errors
          throw new RevRxError(data.detail || 'Request failed', status);
        }

        if (error.code === 'ECONNABORTED') {
          throw new RevRxError(`Request timeout after ${this.timeout}ms`);
        }

        throw new RevRxError(`Request failed: ${error.message}`);
      }
    );

    // Initialize resource namespaces
    this.encounters = new EncounterResource(this);
    this.reports = new ReportResource(this);
    this.webhooks = new WebhookResource(this);
    this.apiKeys = new ApiKeyResource(this);
  }
}

/**
 * Encounter API operations
 */
class EncounterResource {
  constructor(client) {
    this.client = client;
  }

  /**
   * Submit encounter for analysis
   */
  async submit({ clinicalNote, billedCodes, patientAge, patientSex, visitDate }) {
    const data = { clinicalNote, billedCodes };
    if (patientAge) data.patientAge = patientAge;
    if (patientSex) data.patientSex = patientSex;
    if (visitDate) data.visitDate = visitDate;

    const response = await this.client.client.post('/integrations/encounters', data);
    return response.data.encounter;
  }

  /**
   * Get encounter by ID
   */
  async get(encounterId) {
    const response = await this.client.client.get(`/encounters/${encounterId}`);
    return response.data;
  }

  /**
   * List encounters
   */
  async list({ limit = 50, offset = 0 } = {}) {
    const response = await this.client.client.get('/encounters', {
      params: { limit, offset },
    });
    return response.data.encounters;
  }
}

/**
 * Report API operations
 */
class ReportResource {
  constructor(client) {
    this.client = client;
  }

  /**
   * Get report for encounter
   */
  async get(encounterId) {
    const response = await this.client.client.get(`/reports/${encounterId}`);
    return response.data;
  }
}

/**
 * Webhook API operations
 */
class WebhookResource {
  constructor(client) {
    this.client = client;
  }

  /**
   * Create webhook
   */
  async create({ url, events, apiKeyId }) {
    const data = { url, events };
    if (apiKeyId) data.api_key_id = apiKeyId;

    const response = await this.client.client.post('/webhooks', data);
    return response.data;
  }

  /**
   * List webhooks
   */
  async list() {
    const response = await this.client.client.get('/webhooks');
    return response.data.webhooks;
  }

  /**
   * Get webhook by ID
   */
  async get(webhookId) {
    const response = await this.client.client.get(`/webhooks/${webhookId}`);
    return response.data;
  }

  /**
   * Update webhook
   */
  async update(webhookId, { url, events, isActive }) {
    const data = {};
    if (url) data.url = url;
    if (events) data.events = events;
    if (isActive !== undefined) data.is_active = isActive;

    const response = await this.client.client.patch(`/webhooks/${webhookId}`, data);
    return response.data;
  }

  /**
   * Delete webhook
   */
  async delete(webhookId) {
    await this.client.client.delete(`/webhooks/${webhookId}`);
  }

  /**
   * List webhook deliveries
   */
  async listDeliveries(webhookId, { limit = 50, offset = 0 } = {}) {
    const response = await this.client.client.get(`/webhooks/${webhookId}/deliveries`, {
      params: { limit, offset },
    });
    return response.data.deliveries;
  }

  /**
   * Verify webhook signature
   */
  verifySignature(payload, signature, secret) {
    const crypto = require('crypto');
    const expected = crypto.createHmac('sha256', secret).update(payload).digest('hex');
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
  }
}

/**
 * API Key operations
 */
class ApiKeyResource {
  constructor(client) {
    this.client = client;
  }

  /**
   * Create API key
   */
  async create({ name, rateLimit = 100, expiresInDays }) {
    const data = { name, rate_limit: rateLimit };
    if (expiresInDays) data.expires_in_days = expiresInDays;

    const response = await this.client.client.post('/api-keys', data);
    return response.data;
  }

  /**
   * List API keys
   */
  async list() {
    const response = await this.client.client.get('/api-keys');
    return response.data.api_keys;
  }

  /**
   * Get API key by ID
   */
  async get(apiKeyId) {
    const response = await this.client.client.get(`/api-keys/${apiKeyId}`);
    return response.data;
  }

  /**
   * Update API key
   */
  async update(apiKeyId, { name, isActive, rateLimit }) {
    const data = {};
    if (name) data.name = name;
    if (isActive !== undefined) data.is_active = isActive;
    if (rateLimit) data.rate_limit = rateLimit;

    const response = await this.client.client.patch(`/api-keys/${apiKeyId}`, data);
    return response.data;
  }

  /**
   * Delete API key
   */
  async delete(apiKeyId) {
    await this.client.client.delete(`/api-keys/${apiKeyId}`);
  }
}

module.exports = {
  RevRxClient,
  RevRxError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  NotFoundError,
};
