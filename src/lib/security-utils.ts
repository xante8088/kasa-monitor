/**
 * Frontend Security Utilities
 * Provides safe functions for logging, API calls, and input sanitization
 * to prevent log injection and other security vulnerabilities.
 */

/**
 * Sanitizes input for safe logging by removing control characters
 * that could be used for log injection attacks
 */
export function sanitizeForLog(input: unknown): string {
  if (input === null || input === undefined) {
    return 'null';
  }
  
  let stringInput = String(input);
  
  // Remove control characters, newlines, and carriage returns
  // Replace with underscore to maintain log readability
  stringInput = stringInput.replace(/[\r\n\t\x00-\x1f\x7f-\x9f]/g, '_');
  
  // Truncate to prevent log flooding
  if (stringInput.length > 200) {
    stringInput = stringInput.slice(0, 200) + '...[truncated]';
  }
  
  return stringInput;
}

/**
 * Safe console error logging that prevents log injection
 */
export function safeConsoleError(message: string, error?: unknown): void {
  const sanitizedMessage = sanitizeForLog(message);
  
  if (error) {
    const sanitizedError = sanitizeForLog(error);
    console.error(`${sanitizedMessage}: ${sanitizedError}`);
  } else {
    console.error(sanitizedMessage);
  }
}

/**
 * Safe console log that prevents log injection
 */
export function safeConsoleLog(message: string, data?: unknown): void {
  const sanitizedMessage = sanitizeForLog(message);
  
  if (data) {
    const sanitizedData = sanitizeForLog(data);
    console.log(`${sanitizedMessage}: ${sanitizedData}`);
  } else {
    console.log(sanitizedMessage);
  }
}

/**
 * Creates a safe API call with proper URL parameter encoding
 * Prevents untrusted data injection into external API calls
 */
export function createSafeApiUrl(endpoint: string, params?: Record<string, unknown>): string {
  if (!params || Object.keys(params).length === 0) {
    return endpoint;
  }
  
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      // Safely encode both key and value
      const safeKey = encodeURIComponent(String(key));
      const safeValue = encodeURIComponent(String(value));
      searchParams.append(safeKey, safeValue);
    }
  });
  
  const queryString = searchParams.toString();
  return queryString ? `${endpoint}?${queryString}` : endpoint;
}

/**
 * Safe fetch wrapper that ensures proper encoding and error handling
 */
export async function safeFetch(
  endpoint: string, 
  options?: RequestInit & { params?: Record<string, unknown> }
): Promise<Response> {
  const { params, ...fetchOptions } = options || {};
  
  // Create safe URL with encoded parameters
  const safeUrl = createSafeApiUrl(endpoint, params);
  
  try {
    const response = await fetch(safeUrl, fetchOptions);
    return response;
  } catch (error) {
    // Safe error logging
    safeConsoleError(`API call failed for ${endpoint}`, error);
    throw error;
  }
}

/**
 * Sanitizes user input to prevent XSS attacks
 * Note: This is NOT a replacement for server-side validation
 */
export function sanitizeInput(input: string): string {
  if (typeof input !== 'string') {
    return '';
  }
  
  return input
    // Remove potentially dangerous HTML tags
    .replace(/[<>]/g, '')
    // Remove script-related content
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '')
    // Limit length
    .slice(0, 1000);
}

/**
 * Safe localStorage operations that handle errors gracefully
 */
export const safeStorage = {
  getItem(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      safeConsoleError('Failed to read from localStorage', error);
      return null;
    }
  },
  
  setItem(key: string, value: string): boolean {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      safeConsoleError('Failed to write to localStorage', error);
      return false;
    }
  },
  
  removeItem(key: string): boolean {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      safeConsoleError('Failed to remove from localStorage', error);
      return false;
    }
  }
};

/**
 * Validates that a URL is safe (not javascript: or data: protocol)
 */
export function isSafeUrl(url: string): boolean {
  if (typeof url !== 'string') {
    return false;
  }
  
  const lowerUrl = url.toLowerCase().trim();
  
  // Block dangerous protocols
  if (lowerUrl.startsWith('javascript:') || 
      lowerUrl.startsWith('data:') ||
      lowerUrl.startsWith('vbscript:') ||
      lowerUrl.startsWith('file:')) {
    return false;
  }
  
  return true;
}

/**
 * Type guard to check if an error has a message property
 */
export function hasErrorMessage(error: unknown): error is { message: string } {
  return typeof error === 'object' && error !== null && 'message' in error;
}

/**
 * Safe error message extraction
 */
export function getSafeErrorMessage(error: unknown): string {
  if (hasErrorMessage(error)) {
    return sanitizeForLog(error.message);
  }
  
  return sanitizeForLog(error);
}