# 🚀 Deployment Guide

This document outlines the CI/CD pipeline and deployment process for CarIActérologie.

## 🏗️ Infrastructure Overview

### Environments

| Environment | Branch | URL | Purpose |
|-------------|--------|-----|---------|
| **Development** | `development` | https://cariacterologie-dev.streamlit.app | Feature development and testing |
| **Production** | `main` | https://cariacterologie.streamlit.app | Live application for users |

### Branch Strategy

- **`main`** - Production-ready code, stable releases
- **`development`** - Integration branch for features
- **`feature/*`** - Individual feature development
- **`hotfix/*`** - Critical production fixes

## 🔄 CI/CD Pipeline

### Automated Workflows

#### 1. **CI Pipeline** (`.github/workflows/ci.yml`)
Triggers on all PRs and pushes to `main`/`development`:

- ✅ **Code Quality** - Black, isort, flake8, ruff
- 🔒 **Security** - Bandit, safety checks  
- 🧪 **Testing** - pytest with coverage
- ⚙️ **Type Checking** - mypy validation
- 📦 **Dependencies** - Import and config validation

#### 2. **Development Deployment** (`.github/workflows/deploy-dev.yml`)
Triggers on pushes to `development`:

- 🚀 Auto-deploys to development Streamlit app
- 📋 Generates development release notes
- 💾 Creates deployment artifacts
- ⚡ Immediate feedback for testing

#### 3. **Production Deployment** (`.github/workflows/deploy-prod.yml`)
Triggers on pushes to `main` and version tags:

- 🛡️ **Pre-production validation** - comprehensive tests
- 🔐 **Security scans** - thorough security checks
- 📊 **Performance tests** - component initialization benchmarks
- 🎯 **Production deployment** to main Streamlit app
- 🏷️ **GitHub releases** for version tags
- 📈 **Post-deployment monitoring**

## 🚀 Deployment Process

### 1. Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR to development
git push -u origin feature/new-feature
# Create PR: feature/new-feature → development
```

**What happens:**
- ✅ CI pipeline runs automatically
- 👀 Code review process
- ✅ Merge to `development` triggers auto-deployment
- 🧪 Feature available at https://cariacterologie-dev.streamlit.app

### 2. Production Release

```bash
# Create PR from development to main
# After testing in dev environment

# Option 1: Regular release
git checkout main
git merge development
git push origin main

# Option 2: Tagged release
git checkout main  
git merge development
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin main --tags
```

**What happens:**
- 🛡️ Pre-production validation runs
- 🔒 Security and performance checks
- 🚀 Auto-deployment to production
- 🏷️ GitHub release created (if tagged)
- 📊 Post-deployment monitoring

### 3. Hotfix Workflow

```bash
# Create hotfix branch from main
git checkout -b hotfix/critical-fix main

# Make fix and commit
git add .
git commit -m "fix: critical production issue"

# Push and create PR to main
git push -u origin hotfix/critical-fix
# Create PR: hotfix/critical-fix → main

# Also merge back to development
git checkout development
git merge hotfix/critical-fix
git push origin development
```

## ⚙️ Environment Configuration

### Environment Variables

Set these in Streamlit Cloud for each environment:

#### Development Environment
```bash
APP_ENV=development
OPENAI_API_KEY=your_dev_api_key
LANGFUSE_SECRET_KEY=your_dev_langfuse_key  
LANGFUSE_PUBLIC_KEY=your_dev_langfuse_public_key
```

#### Production Environment
```bash
APP_ENV=production
OPENAI_API_KEY=your_prod_api_key
LANGFUSE_SECRET_KEY=your_prod_langfuse_key
LANGFUSE_PUBLIC_KEY=your_prod_langfuse_public_key
```

### Configuration Differences

| Setting | Development | Production |
|---------|-------------|------------|
| **Debug Mode** | ✅ Enabled | ❌ Disabled |
| **Logging Level** | DEBUG | INFO |
| **App Title** | "🧪 CarIActérologie (DEV)" | "🧠 CarIActérologie" |
| **Conversation Branching** | ✅ Enabled | ❌ Disabled |
| **LLM Temperature** | 0.5 | 0.3 |
| **Search Chunks** | 8 | 10 |
| **Email Verification** | ❌ Disabled | ✅ Enabled |

## 🛠️ Streamlit Cloud Setup

### 1. Development App Setup
1. Go to https://share.streamlit.io/
2. Connect your GitHub repository
3. **App URL:** `cariacterologie-dev.streamlit.app`
4. **Branch:** `development`
5. **Main file:** `my_streamlit_app.py`
6. **Advanced settings:**
   ```
   APP_ENV = "development"
   ```

### 2. Production App Setup
1. Go to https://share.streamlit.io/
2. Connect your GitHub repository  
3. **App URL:** `cariacterologie.streamlit.app`
4. **Branch:** `main`
5. **Main file:** `my_streamlit_app.py`
6. **Advanced settings:**
   ```
   APP_ENV = "production"
   ```

## 🔍 Monitoring & Troubleshooting

### Deployment Status
- **GitHub Actions:** Check workflow status in repository Actions tab
- **Streamlit Cloud:** Monitor app status in Streamlit Cloud dashboard
- **Logs:** View app logs in Streamlit Cloud for runtime issues

### Common Issues

#### 1. **FAISS Index Missing**
- **Symptom:** Dummy chunks displayed instead of real content
- **Solution:** App automatically creates index from PDF on first run
- **Monitor:** Check app logs for "Creating FAISS index from PDF" message

#### 2. **Environment Config Not Loading**
- **Symptom:** Wrong app title or settings
- **Solution:** Verify `APP_ENV` is set correctly in Streamlit Cloud
- **Check:** Look for config validation warnings in logs

#### 3. **CI Pipeline Failures**
- **Tests failing:** Check pytest output in Actions logs
- **Security issues:** Review bandit/safety reports in artifacts
- **Type errors:** Fix mypy issues highlighted in CI

### Manual Deployment

If automatic deployment fails:

```bash
# Trigger manual deployment
gh workflow run deploy-dev.yml
gh workflow run deploy-prod.yml
```

Or use GitHub Actions UI with "workflow_dispatch" option.

## 📝 Release Management

### Version Numbering
- **Major:** v2.0.0 - Breaking changes
- **Minor:** v1.4.0 - New features  
- **Patch:** v1.3.1 - Bug fixes

### Release Process
1. Update version in relevant files
2. Create tag: `git tag -a v1.4.0 -m "Release v1.4.0"`
3. Push tag: `git push --tags`
4. GitHub release created automatically
5. Production deployment triggered

### Rollback Strategy
1. **Immediate:** Revert commit and push to main
2. **Tagged release:** Deploy previous tag
3. **Emergency:** Use Streamlit Cloud to manually switch branch/commit

## 🔒 Security Considerations

- 🔑 **API Keys:** Stored securely in Streamlit Cloud secrets
- 🛡️ **Dependencies:** Scanned for vulnerabilities in CI
- 🔒 **Code:** Security scanned with bandit
- 🚫 **Secrets:** Never committed to repository
- 🔄 **Updates:** Regular dependency updates via Dependabot

## 📞 Support

- **CI/CD Issues:** Check GitHub Actions logs
- **App Issues:** Monitor Streamlit Cloud dashboard
- **Emergency:** Direct commit to main for critical fixes
- **Questions:** Review this documentation and workflow files