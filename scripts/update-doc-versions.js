#!/usr/bin/env node

/**
 * Documentation Version Updater
 * Adds or updates version footers in documentation files
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ANSI color codes
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
const VERSION_FOOTER_TEMPLATE = `
---

**Document Version:** {version}  
**Last Updated:** {date}  
**Review Status:** {status}  
**Change Summary:** {summary}`;

// Patterns
const VERSION_PATTERN = /\*\*Document Version:\*\*\s*(\d+\.\d+\.\d+)/i;
const DATE_PATTERN = /\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})/i;
const FOOTER_PATTERN = /^---\s*\n\n\*\*Document Version:\*\*/m;

/**
 * Get current date in ISO format
 */
function getCurrentDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Parse existing version from content
 */
function parseExistingVersion(content) {
  const versionMatch = content.match(VERSION_PATTERN);
  if (versionMatch) {
    return versionMatch[1];
  }
  return null;
}

/**
 * Increment version number
 */
function incrementVersion(version, type = 'patch') {
  const parts = version.split('.').map(Number);
  
  switch (type) {
    case 'major':
      return `${parts[0] + 1}.0.0`;
    case 'minor':
      return `${parts[0]}.${parts[1] + 1}.0`;
    case 'patch':
    default:
      return `${parts[0]}.${parts[1]}.${parts[2] + 1}`;
  }
}

/**
 * Determine document maturity based on content
 */
function determineInitialVersion(content, fileName) {
  const lines = content.split('\n');
  const wordCount = content.split(/\s+/).length;
  
  // Check for completeness indicators
  const hasTodos = /TODO|FIXME|TBD|PLACEHOLDER/i.test(content);
  const hasCodeExamples = /```[\s\S]*?```/.test(content);
  const hasSections = (content.match(/^#{1,3}\s/gm) || []).length;
  
  // Determine version based on maturity
  if (hasTodos || wordCount < 100) {
    return '0.1.0'; // Early draft
  } else if (wordCount < 500 || hasSections < 3) {
    return '0.5.0'; // Basic documentation
  } else if (hasCodeExamples && hasSections >= 5 && wordCount >= 1000) {
    return '1.0.0'; // Complete documentation
  } else {
    return '0.9.0'; // Nearly complete
  }
}

/**
 * Add or update version footer
 */
function updateDocumentFooter(filePath, options = {}) {
  const content = fs.readFileSync(filePath, 'utf8');
  const fileName = path.basename(filePath);
  
  // Check if footer already exists
  const hasFooter = FOOTER_PATTERN.test(content);
  
  if (hasFooter && !options.force) {
    // Update existing footer
    const existingVersion = parseExistingVersion(content);
    const newVersion = options.incrementVersion 
      ? incrementVersion(existingVersion || '1.0.0', options.incrementType)
      : existingVersion || '1.0.0';
    
    const updatedContent = content.replace(
      /^---\s*\n\n\*\*Document Version:\*\*.*$/m,
      `---\n\n**Document Version:** ${newVersion}  \n**Last Updated:** ${getCurrentDate()}  \n**Review Status:** Current  \n**Change Summary:** ${options.summary || 'Updated documentation'}`
    );
    
    return {
      fileName,
      action: 'updated',
      oldVersion: existingVersion,
      newVersion,
      content: updatedContent
    };
  } else {
    // Add new footer
    const initialVersion = options.version || determineInitialVersion(content, fileName);
    const footer = VERSION_FOOTER_TEMPLATE
      .replace('{version}', initialVersion)
      .replace('{date}', getCurrentDate())
      .replace('{status}', options.status || 'Current')
      .replace('{summary}', options.summary || 'Initial version tracking added');
    
    // Remove any existing partial footer and add new one
    let updatedContent = content.replace(/^---[\s\S]*$/m, '').trimEnd();
    updatedContent += '\n' + footer;
    
    return {
      fileName,
      action: 'added',
      oldVersion: null,
      newVersion: initialVersion,
      content: updatedContent
    };
  }
}

/**
 * Get all markdown files
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
 * Interactive prompt
 */
function prompt(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

/**
 * Main function
 */
async function main() {
  console.log(`${colors.cyan}${colors.bright}📝 Documentation Version Updater${colors.reset}`);
  console.log(`${colors.cyan}${'='.repeat(50)}${colors.reset}\n`);
  
  // Parse command line arguments
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const force = args.includes('--force');
  const auto = args.includes('--auto');
  
  if (dryRun) {
    console.log(`${colors.yellow}🔍 DRY RUN MODE - No files will be modified${colors.reset}\n`);
  }
  
  // Check if wiki directory exists
  if (!fs.existsSync(WIKI_DIR)) {
    console.error(`${colors.red}❌ Wiki directory not found: ${WIKI_DIR}${colors.reset}`);
    process.exit(1);
  }
  
  // Get all markdown files
  const files = getMarkdownFiles(WIKI_DIR);
  console.log(`Found ${colors.bright}${files.length}${colors.reset} markdown files\n`);
  
  // Process each file
  const results = [];
  
  for (const filePath of files) {
    const fileName = path.basename(filePath);
    const content = fs.readFileSync(filePath, 'utf8');
    const hasFooter = FOOTER_PATTERN.test(content);
    
    if (!hasFooter || force) {
      // Determine action
      let action = 'add';
      let summary = 'Initial version tracking added';
      
      if (hasFooter) {
        if (!auto) {
          const answer = await prompt(
            `${colors.yellow}${fileName} already has a footer. Update it? (y/n): ${colors.reset}`
          );
          if (answer.toLowerCase() !== 'y') {
            console.log(`  Skipped ${fileName}\n`);
            continue;
          }
        }
        action = 'update';
        summary = 'Documentation updated';
      }
      
      // Update the document
      const result = updateDocumentFooter(filePath, {
        force,
        summary,
        status: 'Current'
      });
      
      results.push(result);
      
      // Write the file if not in dry run mode
      if (!dryRun) {
        fs.writeFileSync(filePath, result.content, 'utf8');
        
        if (result.action === 'added') {
          console.log(`${colors.green}✅ Added footer to ${fileName} (v${result.newVersion})${colors.reset}`);
        } else {
          console.log(`${colors.blue}📝 Updated ${fileName}: v${result.oldVersion} → v${result.newVersion}${colors.reset}`);
        }
      } else {
        if (result.action === 'added') {
          console.log(`${colors.yellow}Would add footer to ${fileName} (v${result.newVersion})${colors.reset}`);
        } else {
          console.log(`${colors.yellow}Would update ${fileName}: v${result.oldVersion} → v${result.newVersion}${colors.reset}`);
        }
      }
    }
  }
  
  // Summary
  console.log(`\n${colors.cyan}${colors.bright}📊 Summary${colors.reset}`);
  console.log(`${colors.cyan}${'─'.repeat(50)}${colors.reset}`);
  
  const added = results.filter(r => r.action === 'added').length;
  const updated = results.filter(r => r.action === 'updated').length;
  
  console.log(`  Files processed: ${results.length}`);
  console.log(`  ${colors.green}Footers added: ${added}${colors.reset}`);
  console.log(`  ${colors.blue}Footers updated: ${updated}${colors.reset}`);
  console.log(`  Skipped: ${files.length - results.length}`);
  
  if (dryRun) {
    console.log(`\n${colors.yellow}This was a dry run. To apply changes, run without --dry-run${colors.reset}`);
  } else if (results.length > 0) {
    console.log(`\n${colors.green}${colors.bright}✅ Documentation version footers updated successfully!${colors.reset}`);
    console.log(`Run ${colors.cyan}npm run check-doc-versions${colors.reset} to verify`);
  }
}

// Run the script
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { updateDocumentFooter, determineInitialVersion };