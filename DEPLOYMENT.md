# SLR Automation App - Deployment Guide

## Quick Deploy Solutions

### Option 1: Heroku (Recommended)
1. Create a new Heroku app
2. Use `requirements-deploy.txt` instead of `requirements.txt`
3. Set environment variables in Heroku dashboard:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY` 
   - `SCOPUS_API_KEY`
   - `SEMANTIC_SCHOLAR_API_KEY`

### Option 2: Railway
1. Connect your GitHub repository
2. Use `requirements-deploy.txt`
3. Set environment variables in Railway dashboard

### Option 3: Render
1. Create new Web Service
2. Connect GitHub repository
3. Use `requirements-deploy.txt`
4. Set environment variables

## Environment Variables Required
```
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
SCOPUS_API_KEY=your_scopus_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key
```

## Buildpack for Heroku (if needed)
```
https://github.com/heroku/heroku-buildpack-apt
```

## Common Issues Fixed
- ✅ Removed lxml dependency to avoid libxslt.so.1 error
- ✅ Added gunicorn for production WSGI server
- ✅ Optimized requirements for cloud deployment
- ✅ Added runtime.txt for Python version specification
