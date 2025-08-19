# Kasa Monitor Plugins

This directory contains plugins that extend Kasa Monitor functionality.

## Plugin Types

- **Device Plugins**: Add support for new device types
- **Integration Plugins**: Connect with external services  
- **Analytics Plugins**: Advanced data processing and reporting
- **Automation Plugins**: Device automation and scheduling
- **Utility Plugins**: Helper tools and utilities

## Plugin Structure

Each plugin should be in its own directory with:

```
my-plugin/
├── manifest.json          # Plugin metadata
├── main.py                # Main plugin class
├── requirements.txt       # Python dependencies (optional)
├── config/                # Configuration files (optional)
└── README.md             # Plugin documentation
```

## Installation

1. **ZIP Installation**: Upload plugin ZIP files through the admin interface
2. **Directory Installation**: Copy plugin directories to this folder
3. **Development**: Create plugins directly in this directory

## Plugin Management

- **Admin Panel**: Manage plugins through Admin → Plugins
- **API**: Use `/api/plugins/*` endpoints
- **CLI**: Plugin management commands (future)

## Getting Started

See `PLUGIN_DEVELOPMENT.md` in the root directory for:
- Plugin development guide
- API reference
- Example plugins
- Best practices

## Security

- All plugins run in sandboxed environments
- Permissions must be explicitly granted
- Code review recommended for production use