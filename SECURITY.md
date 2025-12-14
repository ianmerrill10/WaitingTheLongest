# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Waiting The Longest™ seriously. If you believe you've found a security vulnerability, please follow these steps:

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email security concerns to: security@waitingthelongest.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability within 7 days
- **Updates**: We will keep you informed of our progress
- **Resolution**: We aim to resolve critical issues within 30 days
- **Credit**: With your permission, we will credit you in our security advisory

### Scope

The following are in scope for security reports:
- Production website: waitingthelongest.com
- API endpoints
- Authentication/authorization issues
- Data exposure vulnerabilities
- Cross-site scripting (XSS)
- SQL injection
- Remote code execution
- Server-side request forgery (SSRF)

### Out of Scope

- Denial of service attacks
- Social engineering
- Physical access attacks
- Issues in third-party dependencies (report these upstream)

## Security Measures

### Authentication & Authorization
- Rate limiting on all API endpoints
- Session management with secure cookies
- Input validation on all user inputs

### Data Protection
- All data transmitted over HTTPS
- Database credentials stored securely
- Sensitive configuration via environment variables
- Regular security audits

### Infrastructure
- Regular dependency updates via Dependabot
- Automated security scanning in CI/CD
- Container security scanning
- Secrets scanning in code

### Monitoring
- Error tracking with Sentry
- Access logging
- Anomaly detection

## Security Best Practices for Contributors

1. **Never commit secrets** - Use environment variables
2. **Validate all inputs** - Never trust user data
3. **Use parameterized queries** - Prevent SQL injection
4. **Escape output** - Prevent XSS
5. **Keep dependencies updated** - Check for CVEs
6. **Follow least privilege** - Minimize access rights

## Disclosure Policy

- We follow responsible disclosure principles
- We will coordinate disclosure timing with you
- We may publish a security advisory after the fix is deployed
- We will credit reporters who follow responsible disclosure

Thank you for helping keep Waiting The Longest™ and our users safe! 🐾
