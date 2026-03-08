# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue.** Email security details to the maintainers privately.

Include:
- Description and steps to reproduce
- Potential impact
- Suggested fix (if available)

We will acknowledge within 48 hours and work to resolve within 30 days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x | Yes |
| < 2.0 | No |

## Built-in Security Features

Diogenes v2.5 includes these security measures:

| Feature | Description |
|---------|-------------|
| **Rate limiting** | Sliding-window per-IP limiter (60 req/min default) |
| **Security headers** | CSP, HSTS, X-Content-Type-Options, X-Frame-Options |
| **Session tokens** | SHA-256 hashed, TTL-based, with rotation and invalidation |
| **File upload validation** | Magic bytes check, extension allowlist, filename sanitization, 20MB limit |
| **Input sanitization** | Query validation, path traversal prevention |
| **CORS** | Configurable allowed origins |
| **CI security scan** | Bandit (Python) runs on every push via GitHub Actions |

## Best Practices

### For Users

- Keep dependencies updated (`pip install -r requirements.txt --upgrade`)
- Never commit `.env` files — use `.env.example` as a template
- Use HTTPS in production (the production Docker setup includes nginx with security headers)
- Rotate API keys regularly

### For Developers

- All PRs require review before merging
- Run `bandit -r src/` before pushing to catch security issues
- Never log or expose API keys in error messages
- Validate all user input at API boundaries
