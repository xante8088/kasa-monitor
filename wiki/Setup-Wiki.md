# How to Set Up the GitHub Wiki

This guide explains how to upload these wiki pages to your GitHub repository.

## Method 1: GitHub Web Interface (Easiest)

1. **Enable Wiki in Repository**
   - Go to https://github.com/xante8088/kasa-monitor
   - Click "Settings" tab
   - Scroll to "Features" section
   - Check "Wikis" checkbox

2. **Create Initial Page**
   - Click "Wiki" tab in your repository
   - Click "Create the first page"
   - Set title as "Home"
   - Copy content from `wiki/Home.md`
   - Click "Save Page"

3. **Add Additional Pages**
   - Click "New Page" for each wiki file
   - Use the filename (without .md) as the page title
   - Copy and paste content
   - Save each page

## Method 2: Git Command Line

1. **Clone the Wiki Repository**
```bash
# Wiki repos have a .wiki.git suffix
git clone https://github.com/xante8088/kasa-monitor.wiki.git
cd kasa-monitor.wiki
```

2. **Copy Wiki Files**
```bash
# Copy all wiki files
cp ../kasa-monitor/wiki/*.md .

# Rename if needed (GitHub wiki doesn't need .md extension in links)
# But keeping .md extension is fine
```

3. **Commit and Push**
```bash
git add .
git commit -m "Add comprehensive wiki documentation"
git push origin master  # Wiki repos use 'master' not 'main'
```

## Method 3: Automated Script

Create `upload-wiki.sh`:

```bash
#!/bin/bash
# Script to upload wiki pages to GitHub

REPO="xante8088/kasa-monitor"
WIKI_DIR="wiki"

# Clone wiki repo
git clone "https://github.com/${REPO}.wiki.git" temp-wiki
cd temp-wiki

# Copy all markdown files
cp ../${WIKI_DIR}/*.md .

# Commit and push
git add .
git commit -m "Update wiki documentation"
git push origin master

# Cleanup
cd ..
rm -rf temp-wiki

echo "Wiki uploaded successfully!"
```

## Wiki Structure

The wiki includes these pages:

### Core Documentation
- **Home** - Main wiki page with overview
- **Installation** - Complete installation guide
- **Quick-Start** - 5-minute setup guide
- **FAQ** - Frequently asked questions

### User Guides
- **Dashboard-Overview** - Understanding the interface
- **Device-Management** - Adding and managing devices
- **Energy-Monitoring** - Tracking consumption
- **Cost-Analysis** - Understanding costs
- **Network-Configuration** - Docker networking

### Technical Documentation
- **API-Documentation** - REST API reference
- **Security-Guide** - Security best practices
- **Database-Schema** - Data structure
- **Architecture** - System design

### Administration
- **User-Management** - Roles and permissions
- **System-Configuration** - Advanced settings
- **Backup-Recovery** - Data protection
- **Performance-Tuning** - Optimization

### Development
- **Contributing** - How to contribute
- **Development-Setup** - Local development
- **Plugin-Development** - Extensions

## Page Naming Conventions

GitHub Wiki uses these conventions:
- Spaces in titles become hyphens in URLs
- `.md` extension is optional in links
- Case-insensitive URLs
- Special characters are escaped

## Linking Between Pages

In wiki pages, use:
```markdown
[Link Text](Page-Name)
[Installation Guide](Installation)
[API Docs](API-Documentation)
```

## Adding Images

1. Create `images` folder in wiki
2. Upload images through web interface
3. Reference in markdown:
```markdown
![Alt Text](images/screenshot.png)
```

## Sidebar Navigation

Create `_Sidebar.md`:

```markdown
## Navigation
* [Home](Home)
* **Getting Started**
  * [Installation](Installation)
  * [Quick Start](Quick-Start)
  * [FAQ](FAQ)
* **User Guide**
  * [Dashboard](Dashboard-Overview)
  * [Devices](Device-Management)
  * [Energy](Energy-Monitoring)
* **Technical**
  * [API](API-Documentation)
  * [Security](Security-Guide)
* **Help**
  * [Troubleshooting](Common-Issues)
  * [Support](https://github.com/xante8088/kasa-monitor/issues)
```

## Footer

Create `_Footer.md`:

```markdown

---

**Document Version:** 0.9.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added