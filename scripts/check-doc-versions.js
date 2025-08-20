#!/usr/bin/env node

/**
 * Documentation Version Checker
 * Validates that all documentation files have proper version footers
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

// Configuration
const WIKI_DIR = path.join(__dirname, '..', 'wiki');
const VERSION_PATTERN = /\*\*Document Version:\*\*\s*(\d+\.\d+\.\d+)/i;
const DATE_PATTERN = /\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})/i;
const STATUS_PATTERN = /\*\*Review Status:\*\*\s*(Current|Needs Review|Under Revision|Deprecated)/i;
const SUMMARY_PATTERN = /\*\*Change Summary:\*\*\s*(.+)/i;

// Valid review statuses
const VALID_STATUSES = ['Current', 'Needs Review', 'Under Revision', 'Deprecated'];

/**
 * Check if a file has a valid version footer
 */
function checkDocumentVersion(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const fileName = path.basename(filePath);
  
  const issues = [];
  const info = {};
  
  // Check for version
  const versionMatch = content.match(VERSION_PATTERN);
  if (versionMatch) {
    info.version = versionMatch[1];
    // Validate semantic version format
    if (!/^\d+\.\d+\.\d+$/.test(info.version)) {
      issues.push('Invalid version format (should be X.Y.Z)');
    }
  } else {
    issues.push('Missing Document Version');
  }
  
  // Check for date
  const dateMatch = content.match(DATE_PATTERN);
  if (dateMatch) {
    info.date = dateMatch[1];
    // Validate date format
    const dateObj = new Date(info.date);
    if (isNaN(dateObj.getTime())) {
      issues.push('Invalid date format');
    } else {
      // Check if date is reasonable (not in future, not too old)
      const now = new Date();
      const daysSinceUpdate = Math.floor((now - dateObj) / (1000 * 60 * 60 * 24));
      if (dateObj > now) {
        issues.push('Date is in the future');
      } else if (daysSinceUpdate > 365) {
        issues.push(`Document is ${daysSinceUpdate} days old (consider review)`);
      }
      info.daysSinceUpdate = daysSinceUpdate;
    }
  } else {
    issues.push('Missing Last Updated date');
  }
  
  // Check for review status
  const statusMatch = content.match(STATUS_PATTERN);
  if (statusMatch) {
    info.status = statusMatch[1];
    if (!VALID_STATUSES.includes(info.status)) {
      issues.push(`Invalid review status: ${info.status}`);
    }
  } else {
    issues.push('Missing Review Status');
  }
  
  // Check for change summary
  const summaryMatch = content.match(SUMMARY_PATTERN);
  if (summaryMatch) {
    info.summary = summaryMatch[1].trim();
    if (info.summary.length < 5) {
      issues.push('Change summary too short');
    }
  } else {
    issues.push('Missing Change Summary');
  }
  
  return {
    fileName,
    filePath,
    issues,
    info,
    hasFooter: versionMatch || dateMatch || statusMatch || summaryMatch
  };
}

/**
 * Get all markdown files in a directory
 */
function getMarkdownFiles(dir) {
  const files = [];
  
  function walkDir(currentDir) {
    const entries = fs.readdirSync(currentDir);
    
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry);
      const stat = fs.statSync(fullPath);
      
      if (stat.isDirectory() && entry !== 'node_modules' && entry !== '.git') {
        walkDir(fullPath);
      } else if (stat.isFile() && entry.endsWith('.md')) {
        files.push(fullPath);
      }
    }
  }
  
  walkDir(dir);
  return files;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Main function
 */
function main() {
  console.log(`${colors.cyan}${colors.bright}📚 Documentation Version Checker${colors.reset}`);
  console.log(`${colors.cyan}${'='.repeat(50)}${colors.reset}\n`);
  
  // Check if wiki directory exists
  if (!fs.existsSync(WIKI_DIR)) {
    console.error(`${colors.red}❌ Wiki directory not found: ${WIKI_DIR}${colors.reset}`);
    process.exit(1);
  }
  
  // Get all markdown files
  const files = getMarkdownFiles(WIKI_DIR);
  console.log(`Found ${colors.bright}${files.length}${colors.reset} markdown files in wiki/\n`);
  
  // Check each file
  const results = files.map(checkDocumentVersion);
  
  // Categorize results
  const compliant = results.filter(r => r.issues.length === 0);
  const nonCompliant = results.filter(r => r.issues.length > 0);
  const missingFooter = results.filter(r => !r.hasFooter);
  
  // Display results
  console.log(`${colors.green}${colors.bright}✅ Compliant Documents (${compliant.length})${colors.reset}`);
  if (compliant.length > 0) {
    console.log(`${colors.green}${'─'.repeat(50)}${colors.reset}`);
    for (const doc of compliant) {
      const age = doc.info.daysSinceUpdate !== undefined 
        ? ` (${doc.info.daysSinceUpdate} days old)`
        : '';
      console.log(`  ✓ ${doc.fileName}`);
      console.log(`    Version: ${doc.info.version} | Updated: ${doc.info.date}${age}`);
      console.log(`    Status: ${doc.info.status}`);
    }
  }
  
  if (nonCompliant.length > 0) {
    console.log(`\n${colors.yellow}${colors.bright}⚠️  Documents with Issues (${nonCompliant.length})${colors.reset}`);
    console.log(`${colors.yellow}${'─'.repeat(50)}${colors.reset}`);
    for (const doc of nonCompliant) {
      console.log(`  ⚠ ${doc.fileName}`);
      for (const issue of doc.issues) {
        console.log(`    ${colors.yellow}• ${issue}${colors.reset}`);
      }
      if (doc.info.version || doc.info.date) {
        console.log(`    Current: v${doc.info.version || '?'} | ${doc.info.date || '?'}`);
      }
    }
  }
  
  if (missingFooter.length > 0) {
    console.log(`\n${colors.red}${colors.bright}❌ Documents Missing Version Footer (${missingFooter.length})${colors.reset}`);
    console.log(`${colors.red}${'─'.repeat(50)}${colors.reset}`);
    for (const doc of missingFooter) {
      const stats = fs.statSync(doc.filePath);
      console.log(`  ✗ ${doc.fileName} (${formatFileSize(stats.size)})`);
    }
  }
  
  // Summary statistics
  console.log(`\n${colors.cyan}${colors.bright}📊 Summary${colors.reset}`);
  console.log(`${colors.cyan}${'─'.repeat(50)}${colors.reset}`);
  console.log(`  Total documents: ${files.length}`);
  console.log(`  ${colors.green}Compliant: ${compliant.length} (${Math.round(compliant.length / files.length * 100)}%)${colors.reset}`);
  console.log(`  ${colors.yellow}With issues: ${nonCompliant.length} (${Math.round(nonCompliant.length / files.length * 100)}%)${colors.reset}`);
  console.log(`  ${colors.red}Missing footer: ${missingFooter.length} (${Math.round(missingFooter.length / files.length * 100)}%)${colors.reset}`);
  
  // Review status breakdown
  const statusCounts = {};
  for (const result of results) {
    if (result.info.status) {
      statusCounts[result.info.status] = (statusCounts[result.info.status] || 0) + 1;
    }
  }
  
  if (Object.keys(statusCounts).length > 0) {
    console.log(`\n${colors.cyan}${colors.bright}📋 Review Status Breakdown${colors.reset}`);
    console.log(`${colors.cyan}${'─'.repeat(50)}${colors.reset}`);
    for (const [status, count] of Object.entries(statusCounts)) {
      const percentage = Math.round(count / files.length * 100);
      let statusColor = colors.green;
      if (status === 'Needs Review') statusColor = colors.yellow;
      if (status === 'Under Revision') statusColor = colors.blue;
      if (status === 'Deprecated') statusColor = colors.red;
      console.log(`  ${statusColor}${status}: ${count} (${percentage}%)${colors.reset}`);
    }
  }
  
  // Age analysis
  const ages = results
    .filter(r => r.info.daysSinceUpdate !== undefined)
    .map(r => r.info.daysSinceUpdate);
  
  if (ages.length > 0) {
    const avgAge = Math.round(ages.reduce((a, b) => a + b, 0) / ages.length);
    const oldestAge = Math.max(...ages);
    const newestAge = Math.min(...ages);
    
    console.log(`\n${colors.cyan}${colors.bright}📅 Document Age Analysis${colors.reset}`);
    console.log(`${colors.cyan}${'─'.repeat(50)}${colors.reset}`);
    console.log(`  Average age: ${avgAge} days`);
    console.log(`  Newest document: ${newestAge} days old`);
    console.log(`  Oldest document: ${oldestAge} days old`);
    
    const stale = results.filter(r => r.info.daysSinceUpdate > 180);
    if (stale.length > 0) {
      console.log(`  ${colors.yellow}Documents older than 6 months: ${stale.length}${colors.reset}`);
    }
  }
  
  // Exit code based on compliance
  const exitCode = nonCompliant.length > 0 || missingFooter.length > 0 ? 1 : 0;
  
  console.log(`\n${colors.cyan}${'='.repeat(50)}${colors.reset}`);
  if (exitCode === 0) {
    console.log(`${colors.green}${colors.bright}✅ All documentation is properly versioned!${colors.reset}`);
  } else {
    console.log(`${colors.yellow}${colors.bright}⚠️  Some documentation needs attention${colors.reset}`);
    console.log(`Run ${colors.cyan}npm run update-doc-versions${colors.reset} to add missing footers`);
  }
  
  process.exit(exitCode);
}

// Run the script
if (require.main === module) {
  main();
}

module.exports = { checkDocumentVersion, getMarkdownFiles };