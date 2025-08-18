/**
 * Application version information
 */

// This should match the version in package.json
export const APP_VERSION = '1.0.0';
export const APP_NAME = 'Kasa Monitor';

/**
 * Get formatted version string for display
 */
export function getVersionString(): string {
  return `${APP_NAME} v${APP_VERSION}`;
}

/**
 * Get short version string
 */
export function getShortVersion(): string {
  return `v${APP_VERSION}`;
}