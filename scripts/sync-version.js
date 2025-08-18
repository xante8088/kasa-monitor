#!/usr/bin/env node

/**
 * Script to sync version numbers between package.json and src/lib/version.ts
 * Run this script whenever you update the version to keep them in sync.
 * 
 * Usage: node scripts/sync-version.js
 */

const fs = require('fs');
const path = require('path');

// Read package.json version
const packageJsonPath = path.join(__dirname, '..', 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
const version = packageJson.version;

console.log(`📦 Package.json version: ${version}`);

// Read current version.ts
const versionTsPath = path.join(__dirname, '..', 'src', 'lib', 'version.ts');
const versionTsContent = fs.readFileSync(versionTsPath, 'utf8');

// Update the version in version.ts
const updatedContent = versionTsContent.replace(
  /export const APP_VERSION = '[^']*';/,
  `export const APP_VERSION = '${version}';`
);

// Write updated content
fs.writeFileSync(versionTsPath, updatedContent);

console.log(`✅ Updated src/lib/version.ts to version ${version}`);

// Check if Git tag matches
const { execSync } = require('child_process');
try {
  const latestTag = execSync('git describe --tags --abbrev=0', { encoding: 'utf8' }).trim();
  const tagVersion = latestTag.replace(/^v/, ''); // Remove 'v' prefix if present
  
  console.log(`🏷️  Latest Git tag: ${latestTag} (${tagVersion})`);
  
  if (tagVersion !== version) {
    console.log(`⚠️  WARNING: Version mismatch detected!`);
    console.log(`   Package version: ${version}`);
    console.log(`   Latest Git tag: ${tagVersion}`);
    console.log(`   Consider creating a new tag: git tag v${version}`);
  } else {
    console.log(`✅ Version is in sync with Git tag`);
  }
} catch (error) {
  console.log(`ℹ️  Could not check Git tags: ${error.message}`);
}

console.log(`\n🎯 Version synchronization complete!`);