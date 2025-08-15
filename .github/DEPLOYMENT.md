# Deployment Configuration

## Environment URLs

The CI/CD pipeline supports configurable production and staging URLs through GitHub repository secrets.

### Setting Up Production URL

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `PRODUCTION_URL` | Your production domain URL | `https://monitor.yourdomain.com` |
| `STAGING_URL` | Your staging domain URL (optional) | `https://staging.monitor.yourdomain.com` |

### Smoke Tests

The deployment pipeline includes smoke tests that:
- **Skip automatically** if `PRODUCTION_URL` is not set or uses the default example domain
- **Run health checks** against your configured production URL
- **Fail the deployment** if the health endpoint doesn't respond

### Default Behavior

If no secrets are configured:
- Smoke tests will be skipped with informational messages
- Deployment will still succeed 
- Environment URLs will use placeholder domains

### Example Configuration

```bash
# Set your production URL
PRODUCTION_URL="https://kasa-monitor.yourcompany.com"

# Optional: Set staging URL  
STAGING_URL="https://staging-kasa-monitor.yourcompany.com"
```

After setting these secrets, your deployment pipeline will:
1. Deploy to your actual production environment
2. Run smoke tests against your real domain
3. Update deployment status with correct URLs