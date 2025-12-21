# GitHub Setup Instructions

Follow these steps to upload your Cloud Cost Optimizer project to GitHub.

## Prerequisites
- Git installed on your machine
- GitHub account created
- GitHub CLI (`gh`) installed (optional, but helpful)

---

## Step 1: Review and Clean Up

### 1.1 Check Current Git Status
```bash
cd /Users/amish.kunal/cloud-cost-optimizer
git status
```

### 1.2 Verify .gitignore is in Place
The root `.gitignore` file should already be created. Verify it exists:
```bash
ls -la .gitignore
```

### 1.3 Remove Sensitive Files from Git History (if already committed)
If you've already committed `.env` files or secrets, remove them:

```bash
# Remove .env files from Git tracking (but keep local copies)
git rm --cached backend/.env
git rm --cached frontend/.env
git rm --cached .env

# Remove AWS credentials if accidentally committed
git rm --cached -r .aws/ 2>/dev/null || true

# Commit the removal
git commit -m "Remove sensitive files from tracking"
```

---

## Step 2: Create .env.example Files

### 2.1 Backend .env.example
The file `backend/.env.example` should already exist. Verify:
```bash
ls backend/.env.example
```

### 2.2 Frontend .env.example (if needed)
If your frontend uses environment variables, create:
```bash
# Create frontend/.env.example if needed
# (Currently, frontend doesn't seem to use .env files)
```

---

## Step 3: Stage Files for Initial Commit

### 3.1 Add All Non-Ignored Files
```bash
git add .
```

### 3.2 Review What Will Be Committed
```bash
git status
```

**Important:** Verify that:
- ✅ `.env` files are NOT listed (they should be ignored)
- ✅ `node_modules/` is NOT listed
- ✅ `__pycache__/` directories are NOT listed
- ✅ `*.joblib` model files are listed (if you want to include them) OR excluded (if too large)
- ✅ `llm_cache.db` is NOT listed

### 3.3 Unstage Large Files (if needed)
If model files are too large (>100MB), remove them:
```bash
# Uncomment the model exclusion lines in .gitignore first, then:
git rm --cached backend/app/ml_models/*.joblib
```

---

## Step 4: Create Initial Commit

### 4.1 Make Your First Commit
```bash
git commit -m "Initial commit: Cloud Cost Optimizer

- FastAPI backend with ML-powered cost optimization
- Next.js frontend with analytics dashboard
- XGBoost model for instance downsizing recommendations
- AWS CloudWatch integration for real-time metrics
- LLM-powered explanations using OpenAI API"
```

### 4.2 (Optional) Create Additional Meaningful Commits
If you want a more detailed commit history, you can break it up:

```bash
# Commit backend separately
git add backend/
git commit -m "feat: Add FastAPI backend with ML recommendations API"

# Commit frontend separately
git add frontend/
git commit -m "feat: Add Next.js frontend with analytics dashboard"

# Commit infrastructure
git add docker-compose.yml .gitignore
git commit -m "chore: Add Docker setup and project configuration"
```

---

## Step 5: Create GitHub Repository

### Option A: Using GitHub CLI (Recommended)
```bash
# Authenticate if not already
gh auth login

# Create a new public repository
gh repo create cloud-cost-optimizer \
  --public \
  --description "AI-powered cloud infrastructure cost optimization platform with ML-driven recommendations" \
  --source=. \
  --remote=origin \
  --push
```

### Option B: Using GitHub Web Interface
1. Go to https://github.com/new
2. Repository name: `cloud-cost-optimizer`
3. Description: `AI-powered cloud infrastructure cost optimization platform with ML-driven recommendations`
4. Visibility: **Public** (for portfolio)
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

---

## Step 6: Connect Local Repo to GitHub

### 6.1 Add Remote (if not using GitHub CLI)
```bash
git remote add origin https://github.com/YOUR_USERNAME/cloud-cost-optimizer.git
# Replace YOUR_USERNAME with your GitHub username
```

### 6.2 Verify Remote
```bash
git remote -v
```

---

## Step 7: Push to GitHub

### 7.1 Push Main Branch
```bash
# Rename branch to main if needed
git branch -M main

# Push to GitHub
git push -u origin main
```

### 7.2 If You Get Authentication Errors
Use a Personal Access Token:
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use token as password when pushing:
```bash
git push -u origin main
# Username: your_username
# Password: your_personal_access_token
```

---

## Step 8: Create README.md

### 8.1 Create a Professional README
Create `README.md` in the root directory (see PROJECT_EXPLANATION.md for content).

### 8.2 Commit and Push README
```bash
git add README.md
git commit -m "docs: Add comprehensive README"
git push
```

---

## Step 9: Add Repository Topics/Tags

On GitHub, go to your repository → Settings → Topics, and add:
- `machine-learning`
- `fastapi`
- `nextjs`
- `cloud-computing`
- `cost-optimization`
- `aws`
- `xgboost`
- `finops`
- `python`
- `typescript`

---

## Step 10: Verify Everything is Public

1. Visit: `https://github.com/YOUR_USERNAME/cloud-cost-optimizer`
2. Verify:
   - ✅ No `.env` files are visible
   - ✅ No API keys or secrets are exposed
   - ✅ README displays correctly
   - ✅ Code is properly formatted
   - ✅ All files are present

---

## Security Checklist

Before making the repo public, verify:

- [ ] No `.env` files in repository
- [ ] No API keys hardcoded in source code
- [ ] No AWS credentials in files
- [ ] No database passwords in code (only in `.env.example`)
- [ ] `.gitignore` properly configured
- [ ] All sensitive data removed from Git history (if previously committed)

---

## Optional: Add GitHub Actions (CI/CD)

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Lint
        run: |
          cd backend
          pip install flake8
          flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

---

## Troubleshooting

### "Large files" error
If you get errors about large files:
```bash
# Remove large files from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/app/ml_models/*.joblib" \
  --prune-empty --tag-name-filter cat -- --all
```

### "Authentication failed"
- Use Personal Access Token instead of password
- Or set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### "Repository already exists"
- Delete the empty repo on GitHub first, or
- Use a different repository name

---

## Next Steps

1. **Add a License**: Choose MIT, Apache 2.0, or GPL-3.0
2. **Add Badges**: Use shields.io for tech stack badges
3. **Add Screenshots**: Add screenshots of the UI to README
4. **Write Documentation**: Expand on API documentation
5. **Add Issues Template**: Create `.github/ISSUE_TEMPLATE/`

---

## Summary

Your repository should now be:
- ✅ Publicly accessible on GitHub
- ✅ Free of sensitive information
- ✅ Well-documented with README
- ✅ Properly organized with .gitignore
- ✅ Ready for recruiters to review

