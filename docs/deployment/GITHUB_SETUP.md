# GitHub Setup Guide

This guide will help you prepare Diogenes for publishing to GitHub as an open-source project.

## Pre-Publication Checklist

### 1. Repository Setup

- [ ] Create a new GitHub repository
- [ ] Add repository description: "AI-powered research assistant with multi-agent architecture"
- [ ] Add topics: `ai`, `research`, `llm`, `multi-agent`, `open-source`
- [ ] Enable discussions
- [ ] Set up branch protection for `main`:
  - [ ] Require pull request reviews before merging
  - [ ] Require status checks to pass
  - [ ] Require branches to be up to date

### 2. Files to Commit

The following files have been created and should be committed:

```
Root Level:
├── README.md                      # Project overview
├── LICENSE                        # MIT License
├── CONTRIBUTING.md                # Contribution guidelines
├── CODE_OF_CONDUCT.md            # Community standards
├── SECURITY.md                    # Security policy
├── CHANGELOG.md                   # Version history
├── DEPLOYMENT.md                  # Deployment guide
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── docker-compose.yml             # Docker setup

.github/
├── workflows/
│   ├── tests.yml                 # Automated testing
│   └── security.yml              # Security scanning
├── ISSUE_TEMPLATE/
│   ├── bug_report.md             # Bug report template
│   ├── feature_request.md        # Feature request template
│   ├── documentation.md          # Doc issue template
│   └── question.md               # Question template
└── pull_request_template.md      # PR template

frontend/
├── .env.example                  # Frontend env template
├── .gitignore                    # Frontend-specific ignores
└── [existing files]

config/
├── default.yaml                  # Default config
├── development.yaml              # Dev config
└── production.yaml               # Production config

docs/
├── [existing documentation]

scripts/
├── test_integration.py           # Integration tests
└── [existing scripts]
```

### 3. Sensitive Data Check

Before pushing to GitHub:

```bash
# Check for any .env files or secrets
git status

# Verify no .env files are tracked
git ls-files | grep -E '\.env'

# Look for common secret patterns
grep -r "api_key\|password\|secret" --include="*.py" --include="*.js" --include="*.ts" .

# Check git history (if this is an existing repo)
git log --all --full-history --source -S "api_key\|password\|secret" -- . | head -20
```

If any secrets are found:
```bash
# Remove from git history (use caution!)
git filter-branch --tree-filter 'rm -f .env' HEAD

# Or use BFG Repo-Cleaner
bfg --delete-files .env
```

### 4. Local Testing Before Push

```bash
# 1. Test backend
python -m venv test_venv
source test_venv/bin/activate  # Windows: test_venv\Scripts\activate
pip install -r requirements.txt
pytest tests/ -v

# 2. Test frontend
cd frontend
npm install
npm run build
cd ..

# 3. Test Docker setup
docker-compose up -d searxng
docker-compose ps

# 4. Verify documentation
- [ ] README renders correctly on GitHub
- [ ] All links in docs work
- [ ] Code examples are accurate

# 5. Check for broken symlinks or missing files
find . -type l ! -exec test -e {} \; -print
```

### 5. GitHub Configuration

#### Settings → General
- [ ] Repository visibility: Public
- [ ] Description: "AI-powered research assistant with multi-agent architecture"
- [ ] Website: (optional, if you have one)
- [ ] Topics: ai, research, llm, multi-agent
- [ ] Default branch: main

#### Settings → Branches
- [ ] Set main as default branch
- [ ] Add branch protection rule for main:
  ```
  - Require a pull request before merging
  - Require approvals: 1
  - Require status checks to pass before merging
  - Require branches to be up to date before merging
  ```

#### Settings → Actions
- [ ] Enable GitHub Actions
- [ ] Allow all actions and reusable workflows

#### Settings → Security & analysis
- [ ] Enable Dependabot alerts
- [ ] Enable Dependabot security updates
- [ ] Enable secret scanning

### 6. Initial Commit and Push

```bash
# Initialize git if not already done
git init
git add .

# Create initial commit
git commit -m "Initial commit: Diogenes v2.0.0

- Multi-agent research orchestration
- Real-time streaming with SSE
- Frontend and backend integration
- Comprehensive documentation
- GitHub workflows and templates"

# Add remote
git remote add origin https://github.com/yourusername/diogenes.git

# Create main branch and push
git branch -M main
git push -u origin main

# Verify push was successful
git log --oneline -5
```

### 7. After First Push

- [ ] Verify all files are on GitHub
- [ ] Check workflows are running
- [ ] Verify branch protection is active
- [ ] Update GitHub profile with project link
- [ ] Create first release/tag:
  ```bash
  git tag -a v2.0.0 -m "Initial release: Diogenes v2.0.0"
  git push origin v2.0.0
  ```

### 8. Promote the Project

Once on GitHub:

- [ ] Share on relevant forums:
  - Hacker News (https://news.ycombinator.com)
  - Product Hunt (https://producthunt.com)
  - Reddit: r/MachineLearning, r/OpenSource, r/Python
  - DEV Community (https://dev.to)

- [ ] Add badges to README:
  - GitHub stars
  - License badge
  - Build status
  - Python/Node version support

- [ ] Create documentation:
  - Contributing guide ✅ (already done)
  - Installation guide ✅ (already done)
  - API documentation link

- [ ] Set up project board (optional):
  - Roadmap
  - Bugs
  - Features
  - In Progress

### 9. Community Setup (Optional)

- [ ] Set up Discussions for Q&A
- [ ] Create labels for issues:
  - `bug` (red)
  - `enhancement` (blue)
  - `documentation` (purple)
  - `good-first-issue` (green)
  - `help-wanted` (orange)
  - `question` (yellow)

- [ ] Create milestone for v2.1:
  - Planned features
  - Expected release date

### 10. Ongoing Maintenance

- [ ] Set up Dependabot for dependency updates
- [ ] Monitor security alerts
- [ ] Review and respond to issues promptly
- [ ] Merge pull requests with good quality
- [ ] Keep documentation up-to-date
- [ ] Release new versions regularly

## Common Issues

### Issue: "fatal: bad default revision 'main'"
```bash
# Solution: Create main branch first
git checkout -b main
git add .
git commit -m "initial"
git push -u origin main
```

### Issue: "hint: You may want to configure the global git properties"
```bash
git config --global user.email "your@email.com"
git config --global user.name "Your Name"
```

### Issue: GitHub Actions not running
```bash
# Check .github/workflows/*.yml syntax
yamllint .github/workflows/

# Ensure workflows are committed
git add .github/workflows/
git commit -m "Add GitHub Actions workflows"
```

### Issue: Can't push to repository
```bash
# Check remote
git remote -v

# Update if needed
git remote set-url origin https://github.com/yourusername/diogenes.git

# Try push again
git push -u origin main
```

## Next Steps

1. Follow the checklist above
2. Commit all changes to local repo
3. Push to GitHub
4. Monitor issues and PRs
5. Continue development based on community feedback
6. Plan v2.1 release

## Support

If you have questions about open-sourcing:
- GitHub's Open Source Guide: https://opensource.guide
- Open Source Initiative: https://opensource.org
- Community resources in CONTRIBUTING.md

---

**Congratulations!** You're ready to share Diogenes with the world! 🌟
