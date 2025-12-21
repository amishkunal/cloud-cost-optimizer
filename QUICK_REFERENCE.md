# Quick Reference - GitHub Upload Checklist

## Pre-Upload Checklist

- [ ] Review `.gitignore` (already created)
- [ ] Verify no `.env` files are tracked: `git status | grep .env`
- [ ] Verify `node_modules/` is ignored: `git status | grep node_modules`
- [ ] Create `backend/.env.example` (template provided in GITHUB_SETUP.md)
- [ ] Review `PROJECT_EXPLANATION.md` for README content

## Quick Commands

```bash
# 1. Check what will be committed
git status

# 2. Add all files (respects .gitignore)
git add .

# 3. Create initial commit
git commit -m "Initial commit: Cloud Cost Optimizer"

# 4. Create GitHub repo (if using GitHub CLI)
gh repo create cloud-cost-optimizer --public --source=. --push

# 5. Or add remote manually
git remote add origin https://github.com/YOUR_USERNAME/cloud-cost-optimizer.git
git push -u origin main
```

## Files to Verify Are NOT Committed

- `backend/.env`
- `frontend/.env` (if exists)
- `*.key`, `*.pem`
- `llm_cache.db`
- `__pycache__/` directories
- `node_modules/`

## Files That SHOULD Be Committed

- `backend/.env.example` (template, no secrets)
- `backend/requirements.txt`
- `frontend/package.json`
- `docker-compose.yml`
- All source code files
- Documentation files (`.md`)

## Security Reminder

Before pushing, double-check:
```bash
# Search for potential secrets in code
grep -r "AKIA" backend/ frontend/  # AWS access keys
grep -r "sk-" backend/ frontend/   # OpenAI keys
grep -r "password" backend/app/config.py  # Should only have defaults
```

If any secrets are found, remove them and use environment variables instead.

