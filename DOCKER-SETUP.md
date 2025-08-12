# 🔐 Docker Hub Authentication Setup Guide

## Quick Fix for Authentication Error

If you're seeing this error:
```
ERROR: failed to fetch oauth token: unexpected status from GET request to https://auth.docker.io/token: 401 Unauthorized
```

Follow these steps to fix it:

## Step 1: Create Docker Hub Access Token

1. **Login to Docker Hub**: https://hub.docker.com
2. Click your **username** (top right) → **Account Settings**
3. Go to **Security** tab
4. Scroll to **Access Tokens** section
5. Click **New Access Token**
6. Fill in:
   - **Access Token Description**: `GitHub Actions - Kasa Monitor`
   - **Access permissions**: Select `Read, Write, Delete`
7. Click **Generate**
8. **⚠️ IMPORTANT**: Copy the token NOW! It looks like: `dckr_pat_AbCdEfGhIjKlMnOpQrStUvWxYz`

## Step 2: Add Secrets to GitHub

1. Go to your repository: https://github.com/xante8088/kasa-monitor
2. Click **Settings** (in the repository, not your profile)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Add these Repository secrets:

### Secret 1: DOCKER_USERNAME
- Click **New repository secret**
- **Name**: `DOCKER_USERNAME`
- **Secret**: Your Docker Hub username (e.g., `xante8088`)
- ⚠️ **NOT your email address!**
- Click **Add secret**

### Secret 2: DOCKER_PASSWORD  
- Click **New repository secret**
- **Name**: `DOCKER_PASSWORD`
- **Secret**: Paste the access token from Step 1 (starts with `dckr_pat_`)
- ⚠️ **NOT your Docker Hub password!**
- Click **Add secret**

## Step 3: Verify Your Setup

### Check Your Secrets
Your repository secrets should look like this:

| Secret | Example Value | Common Mistakes |
|--------|---------------|-----------------|
| DOCKER_USERNAME | `xante8088` | ❌ Using email instead of username |
| DOCKER_PASSWORD | `dckr_pat_AbCd...` | ❌ Using password instead of token |

### Test Your Token Locally
```bash
# Test your token works
echo "YOUR_TOKEN_HERE" | docker login -u YOUR_USERNAME --password-stdin

# Should output: Login Succeeded
```

## Step 4: Re-run GitHub Action

1. Go to **Actions** tab in your repository
2. Click on the failed workflow
3. Click **Re-run all jobs**

## Troubleshooting

### Still Getting 401 Error?

1. **Wrong Username Format**
   - ✅ Correct: `xante8088` (just username)
   - ❌ Wrong: `xante8088@email.com` (email)
   - ❌ Wrong: `https://hub.docker.com/u/xante8088` (URL)

2. **Wrong Token Format**
   - ✅ Correct: `dckr_pat_xxxxxxxxxxxxxxxxxxxxx`
   - ❌ Wrong: Your Docker Hub password
   - ❌ Wrong: GitHub Personal Access Token

3. **Token Permissions**
   - Make sure token has `Read, Write, Delete` permissions
   - If unsure, create a new token with correct permissions

4. **Expired Token**
   - Docker Hub tokens can expire
   - Create a new token if yours is old

### Check Current Secrets
To see if secrets are set (but not their values):
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. You should see both `DOCKER_USERNAME` and `DOCKER_PASSWORD` listed
3. Click **Update** to change a secret's value

### Debug in GitHub Actions
The workflow now includes verification that will show:
- If secrets are set (without revealing them)
- Username length (to verify it's not empty)

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Wrong credentials | Create new access token |
| Repository not found | Wrong username in image name | Update docker-compose.yml |
| Permission denied | Token lacks permissions | Create token with Read, Write, Delete |
| Secret not found | Typo in secret name | Check exact spelling: DOCKER_USERNAME |

## Need More Help?

1. **Verify Docker Hub Account**: 
   - Can you login at https://hub.docker.com?
   - Do you have a repository named `kasa-monitor`?

2. **Check GitHub Actions Log**:
   - Go to Actions tab → Click failed run → Check "Verify secrets are set" step

3. **Create Fresh Token**:
   - Delete old token in Docker Hub
   - Create new one with all permissions
   - Update GitHub secret immediately

---

Once properly configured, your GitHub Actions will automatically build and push Docker images to Docker Hub on every commit to main branch! 🚀