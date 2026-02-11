# 🚀 Pre-Push Checklist for GitHub

Before pushing to GitHub, verify the following:

## ✅ Security Checklist

### 1. No Secrets or API Keys
```powershell
# Search for potential secrets
Select-String -Path . -Pattern "API_KEY|SECRET|PASSWORD|TOKEN" -Include "*.py","*.ts","*.tsx","*.js","*.yaml" -Exclude ".env.example" -Recurse
```

**Verify:**
- [ ] No hardcoded API keys
- [ ] No hardcoded passwords
- [ ] No secret tokens in code
- [ ] `.env` files are gitignored (only `.env.example` should be committed)

### 2. Database Files Not Included
```powershell
# Check for database files
Get-ChildItem -Recurse -Include "*.db","*.sqlite","*.sqlite3" | Select-Object FullName
```

**Verify:**
- [ ] No `.db` or `.sqlite` files in git
- [ ] `data/` directory is gitignored
- [ ] All database files are excluded

### 3. Dependencies Properly Managed
**Verify:**
- [ ] `node_modules/` is gitignored
- [ ] `__pycache__/` is gitignored
- [ ] `venv/` is gitignored
- [ ] Only `package.json` and `requirements.txt` are committed (not lock files - optional)

### 4. No Personal Data
**Verify:**
- [ ] No personal research data in git
- [ ] No user session data
- [ ] No cached responses with sensitive content
- [ ] `_bmad/` and `_bmad-output/` are gitignored

## 🔍 Code Quality Checklist

### 1. Python Code Compiles
```powershell
# Test main entry points
python -m py_compile main.py run_api.py
python -c "import src.api.app"
```

**Verify:**
- [ ] No syntax errors
- [ ] All imports work
- [ ] Main files compile

### 2. Frontend Builds
```powershell
cd frontend
npm run typecheck
npm run build
```

**Verify:**
- [ ] TypeScript compiles without errors
- [ ] Build completes successfully
- [ ] No critical warnings

### 3. Tests Pass (Optional but Recommended)
```powershell
# Backend tests
pytest tests/ -v

# Frontend tests (if any)
cd frontend
npm test
```

## 📁 Files to Commit

### ✅ Should Be Committed
- [ ] Source code (`src/`, `frontend/`)
- [ ] Configuration templates (`.env.example`, `config/*.yaml`)
- [ ] Documentation (`docs/`, `README.md`, etc.)
- [ ] Docker configuration (`docker-compose.yml`, `searxng/Dockerfile`)
- [ ] Package manifests (`requirements.txt`, `package.json`)
- [ ] Scripts (`*.ps1`, `scripts/`)
- [ ] Tests (`tests/`)
- [ ] `.gitignore`
- [ ] License file (`LICENSE`)
- [ ] GitHub workflows (`.github/`)

### ❌ Should NOT Be Committed
- [ ] Environment files (`.env`, `frontend/.env.local`)
- [ ] Database files (`*.db`, `*.sqlite`)
- [ ] Node modules (`node_modules/`)
- [ ] Python cache (`__pycache__/`, `*.pyc`)
- [ ] Virtual environment (`venv/`, `.venv`)
- [ ] Build outputs (`dist/`, `build/`)
- [ ] Data directory (`data/`)
- [ ] Log files (`*.log`, `logs/`)
- [ ] IDE settings (`.vscode/`, `.idea/`)
- [ ] OS files (`.DS_Store`, `Thumbs.db`)
- [ ] Personal tools (`_bmad/`, `.gemini/`)
- [ ] Research outputs (optional - depends on project goals)

## 🎯 Final Verification

### Run the Pre-Push Script
```powershell
# Check for sensitive files
Get-ChildItem -Recurse | Where-Object { 
    $_.Name -match '\.(env|db|sqlite|key|pem)$' -and 
    $_.Name -notmatch 'example'
} | Select-Object FullName
```

**Expected:** Only `.env.example` files should appear

### Initialize Git (if not done)
```powershell
# Initialize repository
git init

# Add remote (replace with your GitHub URL)
git remote add origin https://github.com/YOUR_USERNAME/diogenes.git

# Check what will be committed
git status
git add .
git status

# Review files to be committed
git diff --cached --name-only
```

### Before First Push
```powershell
# Commit
git commit -m "Initial commit: Diogenes AI Research Assistant"

# Push to GitHub
git push -u origin main
```

## 🔐 Post-Push Security

After pushing to GitHub:

1. **Check GitHub Security Alerts**
   - Go to repository → Security → Secret scanning
   - Review any alerts

2. **Verify .gitignore Worked**
   ```powershell
   # On GitHub, check that these aren't present:
   # - .env files
   # - database files
   # - node_modules
   # - __pycache__
   ```

3. **Add Repository Secrets (for CI/CD)**
   - Go to Settings → Secrets and variables → Actions
   - Add any secrets needed for workflows

4. **Enable Branch Protection** (recommended)
   - Settings → Branches → Add rule
   - Require PR reviews
   - Require status checks

## 📝 Common Issues

### Issue: "remote rejected" or "file too large"
**Solution:** Git has a file size limit. Check for large files:
```powershell
Get-ChildItem -Recurse -File | Where-Object { $_.Length -gt 50MB } | Select-Object FullName, Length
```

### Issue: Accidentally committed secrets
**Solution:** 
1. Remove from history: `git filter-branch` or `BFG Repo-Cleaner`
2. Rotate the exposed secrets immediately
3. Push force: `git push --force`

### Issue: Too many files being committed
**Solution:** Review `.gitignore` and verify it matches this checklist

## ✅ Ready to Push!

Once all items are checked:
```powershell
# Final check
git status

# Push
git push
```

---

**Last Updated:** February 12, 2026

💡 **Tip:** Keep this file as a reference for all future updates!
