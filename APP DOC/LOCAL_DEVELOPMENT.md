# 💻 Local Development Guide

This guide explains how to work with different branches and environments on your local machine.

## 🌿 Understanding Git Branches Locally

Your local repository can have **multiple versions** of the codebase:

```bash
# Check all branches
git branch -a

# Current output:
# * development    ← You are here (active branch)
#   main           ← Production code version
#   remotes/origin/development  ← Remote development
#   remotes/origin/main        ← Remote production
```

## 🔄 Branch Switching Workflow

### **Current Status**
```bash
git status
# On branch development
```

### **Switch Between Branches**

#### **Work on Development Features:**
```bash
# Already on development branch
git checkout development

# Start the app in development mode
run-dev.bat
# App runs at http://localhost:8501 with development config
# Title shows: "🧪 CarIActérologie (DEV)"
```

#### **Test Production Locally:**
```bash
# Switch to main branch (production code)
git checkout main

# Start the app in production mode  
run-prod.bat
# App runs at http://localhost:8502 with production config
# Title shows: "🧠 CarIActérologie"
```

#### **Create New Feature:**
```bash
# Start from development
git checkout development
git pull origin development

# Create feature branch
git checkout -b feature/my-new-feature

# Work on your feature...
# Test with: run-dev.bat
```

## 🚀 Practical Daily Workflow

### **Morning Setup:**
```bash
# 1. Check which branch you're on
git branch

# 2. Switch to development if needed
git checkout development

# 3. Get latest changes
git pull origin development

# 4. Start development server
run-dev.bat
```

### **Working on Features:**
```bash
# 1. Create feature branch
git checkout -b feature/awesome-feature

# 2. Make changes to code
# 3. Test locally with development config
run-dev.bat

# 4. Commit and push
git add .
git commit -m "feat: add awesome feature"
git push -u origin feature/awesome-feature

# 5. Create PR: feature/awesome-feature → development
```

### **Testing Production Code Locally:**
```bash
# 1. Switch to main branch
git checkout main
git pull origin main

# 2. Test with production settings
run-prod.bat

# 3. Verify production behavior
# - Less verbose logging
# - Production optimizations
# - Conservative LLM settings
```

## ⚙️ Environment Differences

| Aspect | Development Branch | Main Branch |
|--------|-------------------|-------------|
| **Command** | `run-dev.bat` | `run-prod.bat` |
| **Port** | 8501 | 8502 |
| **APP_ENV** | development | production |
| **Title** | "🧪 CarIActérologie (DEV)" | "🧠 CarIActérologie" |
| **Debug** | ✅ Enabled | ❌ Disabled |
| **Logging** | DEBUG level | INFO level |
| **LLM Temperature** | 0.5 | 0.3 |
| **Features** | Experimental enabled | Stable only |

## 📁 Your File Structure

```
CarIacterologie_streamlit/
├── .env.development     ← Development environment vars
├── .env.production      ← Production environment vars  
├── run-dev.bat          ← Start development mode
├── run-prod.bat         ← Start production mode
├── config/
│   └── environments/    ← Environment-specific configs
│       ├── development.py
│       └── production.py
└── my_streamlit_app.py  ← Main app (same code, different config)
```

## 🎯 Key Concepts

### **Same Code, Different Behavior**
- The **same `my_streamlit_app.py` file** runs differently based on:
  - Which **branch** you're on (code version)
  - Which **environment** variables are set (behavior)

### **Branch = Code Version**
```bash
# Development branch = latest features
git checkout development
# main branch = stable production code  
git checkout main
```

### **Environment = App Behavior**
```bash
# Development behavior
APP_ENV=development run-dev.bat

# Production behavior  
APP_ENV=production run-prod.bat
```

## 🔧 Setup Your Environment

### **1. Add Your API Keys**

Edit `.env.development`:
```bash
APP_ENV=development
OPENAI_API_KEY=your_actual_dev_key_here
LANGFUSE_SECRET_KEY=your_actual_dev_langfuse_key
```

Edit `.env.production`:
```bash
APP_ENV=production  
OPENAI_API_KEY=your_actual_prod_key_here
LANGFUSE_SECRET_KEY=your_actual_prod_langfuse_key
```

### **2. Test Both Environments**

```bash
# Test development
git checkout development
run-dev.bat
# Visit http://localhost:8501 - should show DEV in title

# Test production (in another terminal)
git checkout main  
run-prod.bat
# Visit http://localhost:8502 - should show production title
```

## 🚨 Common Scenarios

### **"I want to test my feature"**
```bash
git checkout development  # or your feature branch
run-dev.bat              # development environment
```

### **"I want to see what production looks like"**
```bash
git checkout main        # production code
run-prod.bat            # production environment  
```

### **"I want to develop a new feature"**
```bash
git checkout development
git checkout -b feature/my-feature
run-dev.bat             # develop with live reload
```

### **"I want to test production behavior with development code"**
```bash
git checkout development  # development code
run-prod.bat             # production environment settings
```

## 🔄 Branch Synchronization

### **Keep Development Updated:**
```bash
git checkout development
git pull origin development
```

### **Update Main from Development:**
```bash
# After testing in development, promote to production
git checkout main
git merge development
git push origin main
```

## 🎉 Summary

- **Your local machine** can switch between code versions (branches)
- **Each branch** has the same files but different content
- **Environment variables** control app behavior  
- **`run-dev.bat`** = development mode
- **`run-prod.bat`** = production mode
- **Switch branches** with `git checkout <branch>`

You have **one local repository** that can show **different versions** of your app! 🚀