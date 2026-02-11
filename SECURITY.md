# Diogenes Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Diogenes, please do not open a public GitHub issue. Instead, please follow these responsible disclosure guidelines:

### How to Report

1. **Email**: Send details to [security@example.com] (replace with actual email)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

3. **Do Not**:
   - Disclose the vulnerability publicly before we've had a chance to fix it
   - Access data that isn't yours
   - Modify or delete data
   - Disrupt service availability

### Our Commitment

We commit to:
- Acknowledge receipt within 48 hours
- Provide regular updates on progress
- Credit the reporter when the fix is released (if desired)
- Work to resolve the issue within 30 days when possible

## Supported Versions

| Version | Supported          | End of Support |
|---------|-------------------|-----------------|
| 2.x     | ✅ Yes             | TBD            |
| 1.x     | ❌ No              | Deprecated     |
| < 1.0   | ❌ No              | N/A            |

## Security Best Practices

### For Users

1. **Keep Updated**: Regularly update Diogenes and dependencies
   ```bash
   git pull origin main
   pip install -r requirements.txt --upgrade
   ```

2. **Protect Credentials**:
   - Never commit `.env` files
   - Use strong API keys
   - Rotate secrets regularly

3. **Network Security**:
   - Use HTTPS in production
   - Restrict API access with firewalls
   - Use strong authentication

4. **Dependency Management**:
   - Regularly check for vulnerabilities
   - Update dependencies promptly
   - Review dependency changelogs

### For Developers

1. **Code Review**: All PRs require review before merging
2. **Dependency Scanning**: Automated checks for vulnerable dependencies
3. **Secrets Detection**: CI/CD prevents committing secrets
4. **Input Validation**: Always validate user input
5. **Error Handling**: Don't leak sensitive information in errors

## Known Issues

None currently. If you discover one, please report it responsibly.

## Security Advisories

When we release security fixes, we will:
1. Create a GitHub Security Advisory
2. Release a patch version
3. Notify users through release notes
4. Update this policy with details

---

Thank you for helping keep Diogenes secure! 🔒
