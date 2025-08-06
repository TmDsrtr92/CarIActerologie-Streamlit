# 🚀 CI/CD Setup Instructions

This guide will help you set up the complete CI/CD pipeline for CarIActérologie.

## 📋 Prerequisites

- GitHub repository with admin access
- Streamlit Cloud account
- OpenAI API key
- Langfuse account (optional)

## 🏗️ Step-by-Step Setup

### 1. GitHub Repository Setup

#### Create Branches
```bash
# Create development branch
git checkout -b development
git push -u origin development

# Set up branch protection rules in GitHub Settings > Branches
# - Require pull request reviews before merging
# - Require status checks to pass before merging
# - Include administrators in restrictions
```

#### Configure Secrets
Go to **Settings > Secrets and Variables > Actions** and add:

```
OPENAI_API_KEY_DEV=your_development_api_key
OPENAI_API_KEY_PROD=your_production_api_key
LANGFUSE_SECRET_KEY_DEV=your_dev_langfuse_secret  
LANGFUSE_SECRET_KEY_PROD=your_prod_langfuse_secret
LANGFUSE_PUBLIC_KEY_DEV=your_dev_langfuse_public
LANGFUSE_PUBLIC_KEY_PROD=your_prod_langfuse_public
```

#### Set up Environments
Go to **Settings > Environments** and create:

1. **development**
   - No restrictions
   - Add environment secrets with _DEV suffix

2. **production** 
   - Require reviews from 1 person
   - Restrict to `main` branch only
   - Add environment secrets with _PROD suffix

### 2. Streamlit Cloud Setup

#### Development App
1. Go to https://share.streamlit.io/
2. **New app** > **From existing repo**
3. **Repository:** `YourUsername/CarIActerologie-Streamlit`
4. **Branch:** `development`  
5. **Main file path:** `my_streamlit_app.py`
6. **App URL:** `your-app-name-dev` (custom subdomain)
7. **Advanced settings:**
   ```toml
   [app]
   APP_ENV = "development"
   
   [secrets]
   OPENAI_API_KEY = "your_dev_api_key"
   LANGFUSE_SECRET_KEY = "your_dev_langfuse_secret"
   LANGFUSE_PUBLIC_KEY = "your_dev_langfuse_public"
   ```

#### Production App  
1. **New app** > **From existing repo**
2. **Repository:** `YourUsername/CarIActerologie-Streamlit`
3. **Branch:** `main`
4. **Main file path:** `my_streamlit_app.py` 
5. **App URL:** `your-app-name` (main subdomain)
6. **Advanced settings:**
   ```toml
   [app]
   APP_ENV = "production"
   
   [secrets]
   OPENAI_API_KEY = "your_prod_api_key"
   LANGFUSE_SECRET_KEY = "your_prod_langfuse_secret"
   LANGFUSE_PUBLIC_KEY = "your_prod_langfuse_public"
   ```

### 3. Local Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests locally
pytest tests/ -v

# Run code quality checks
black .
isort .
flake8 .
mypy .
```

## 🔄 Workflow Usage

### Development Workflow

```bash
# 1. Create feature branch
git checkout development
git pull origin development
git checkout -b feature/awesome-feature

# 2. Make changes and test locally
# ... make your changes ...
pytest tests/
black .

# 3. Commit and push
git add .
git commit -m "feat: add awesome feature"
git push -u origin feature/awesome-feature

# 4. Create Pull Request
# Create PR: feature/awesome-feature → development
# CI will run automatically
# After approval, merge to development
# Auto-deploys to dev environment
```

### Production Release

```bash
# 1. Create release PR
# Create PR: development → main
# CI validation runs automatically

# 2. After testing in dev, merge to main
git checkout main
git merge development
git push origin main

# 3. (Optional) Create tagged release
git tag -a v1.4.0 -m "Release v1.4.0: New Features"
git push origin --tags
# This triggers production deployment with GitHub release
```

## 🧪 Testing the Pipeline

### Test CI Pipeline
```bash
# Create a test PR to development
git checkout -b test/ci-pipeline
echo "# Test CI" >> test-ci.md
git add test-ci.md
git commit -m "test: verify CI pipeline"
git push -u origin test/ci-pipeline
# Create PR and observe CI running
```

### Test Development Deployment
```bash
# Push to development branch
git checkout development
echo "console.log('Dev deployment test')" >> test-deploy.js
git add test-deploy.js
git commit -m "test: verify dev deployment"
git push origin development
# Check GitHub Actions for deployment workflow
# Verify changes appear in dev app
```

### Test Production Deployment
```bash
# Create production release
git checkout main
git merge development
git tag -a v1.0.0-test -m "Test production deployment"
git push origin main --tags
# Check GitHub Actions for production workflow
# Verify changes appear in production app
```

## 📊 Monitoring & Validation

### Check Deployment Status
- **GitHub Actions:** Repository > Actions tab
- **Streamlit Dev:** https://your-app-name-dev.streamlit.app
- **Streamlit Prod:** https://your-app-name.streamlit.app

### Validate Environment Configuration
```bash
# Check if environment is correctly detected
# Look for these in app logs:

# Development:
# "🧪 CarIActérologie (DEV)" in title
# Debug logging enabled
# Development features enabled

# Production:  
# "🧠 CarIActérologie" in title
# Production optimizations active
# Error-only logging
```

### Common Issues & Solutions

#### 1. **CI Tests Failing**
```bash
# Run tests locally to debug
pytest tests/ -v --tb=long

# Check specific failures
pytest tests/test_specific.py -v
```

#### 2. **Environment Not Loading**
```bash
# Verify APP_ENV is set in Streamlit Cloud
# Check app logs for configuration warnings
# Ensure environment files are committed
```

#### 3. **FAISS Index Issues**
```bash
# Check app startup logs for:
# "Creating FAISS index from PDF: documents/traite_caracterologie.pdf"
# Should see "Successfully created FAISS index with 336 vectors"
```

#### 4. **Deployment Not Triggering**
```bash
# Verify branch names match exactly
# Check GitHub Actions workflow files are in main branch
# Ensure Streamlit Cloud is watching correct branch
```

## 🔐 Security Best Practices

- ✅ **Never commit secrets** to repository
- ✅ **Use environment-specific API keys**  
- ✅ **Enable branch protection rules**
- ✅ **Require PR reviews for production**
- ✅ **Run security scans in CI**
- ✅ **Use least-privilege access**

## 📈 Next Steps

1. **Monitor Performance:** Set up application monitoring
2. **User Feedback:** Implement feedback collection
3. **Analytics:** Add usage analytics (respecting privacy)
4. **Scaling:** Plan for increased usage
5. **Backups:** Regular backup strategy
6. **Documentation:** Keep deployment docs updated

## 🆘 Emergency Procedures

### Quick Rollback
```bash
# If production has critical issues:
# 1. Revert the problematic commit
git revert HEAD
git push origin main

# 2. Or deploy previous working version
git reset --hard <previous-working-commit>  
git push --force origin main

# 3. Or use Streamlit Cloud to manually change branch/commit
```

### Emergency Hotfix
```bash
# For critical production fixes:
git checkout -b hotfix/critical-fix main
# ... make minimal fix ...
git commit -m "hotfix: critical production issue"
git push -u origin hotfix/critical-fix
# Create PR directly to main
# Merge after minimal testing
# Don't forget to merge back to development!
```

## 📞 Support Contacts

- **Technical Issues:** Check GitHub Issues
- **CI/CD Problems:** Review GitHub Actions logs  
- **App Deployment:** Streamlit Cloud dashboard
- **Emergency:** Direct commit to main (use sparingly)

---

🎉 **Congratulations!** Your CI/CD pipeline is now set up for professional development and deployment workflows.