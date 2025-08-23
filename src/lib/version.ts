/**
 * Application version information
 * 
 * This file should be kept in sync with package.json version.
 * For production deployments, consider using a build-time script
 * to automatically sync this with package.json.
 */

// This should match the version in package.json
export const APP_VERSION = '1.1.1';
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

/**
 * Get version with build info for development
 */
export function getVersionWithBuild(): string {
  const isDev = process.env.NODE_ENV === 'development';
  const buildSuffix = isDev ? '-dev' : '';
  return `v${APP_VERSION}${buildSuffix}`;
}

/**
 * Check if running the latest version by comparing with GitHub releases
 * This function can be used to show update notifications
 */
export async function checkForUpdates(): Promise<{
  isLatest: boolean;
  currentVersion: string;
  latestVersion: string;
  updateAvailable: boolean;
}> {
  try {
    // In a real implementation, you would fetch from GitHub API
    // For now, we'll assume current version is latest
    const currentVersion = APP_VERSION;
    
    // This would normally fetch from: https://api.github.com/repos/xante8088/kasa-monitor/releases/latest
    // For demo purposes, we'll return current state
    return {
      isLatest: true,
      currentVersion,
      latestVersion: currentVersion,
      updateAvailable: false
    };
  } catch (error) {
    // If check fails, assume current version is latest
    return {
      isLatest: true,
      currentVersion: APP_VERSION,
      latestVersion: APP_VERSION,
      updateAvailable: false
    };
  }
}