---
description: Command from Security Essentials
---

# Security Best Practices for Claude Code

## Overview
This guide provides essential security practices when using Claude Code in your projects.

## Environment Variables and Secrets

### Never Commit Secrets
```bash
# Bad - Never do this
API_KEY=sk-1234567890abcdef

# Good - Use environment variables
API_KEY=${API_KEY}

# Better - Use secret management
aws secretsmanager get-secret-value --secret-id my-api-key
```

### Use .env Files Safely
```bash
# Create .env file
touch .env

# Add to .gitignore immediately
echo ".env" >> .gitignore

# Use dotenv for loading
npm install dotenv
```

## File Permissions

### Protect Sensitive Files
```bash
# Set restrictive permissions on private keys
chmod 600 ~/.ssh/id_rsa

# Protect configuration files
chmod 644 config.json

# Secure directories
chmod 700 ~/.claude
```

## Command Safety

### Validate User Input
```javascript
// Never do this
const command = `rm -rf ${userInput}`;

// Do this instead
const sanitized = userInput.replace(/[^a-zA-Z0-9]/g, '');
const command = `rm -f /tmp/${sanitized}`;
```

### Use Safe Commands
```bash
# Dangerous
rm -rf *

# Safer
rm -i *.tmp

# Safest
find . -name "*.tmp" -type f -delete
```

## AWS Security

### Use IAM Roles
```typescript
// Don't hardcode credentials
const client = new S3Client({
  credentials: {
    accessKeyId: "AKIA...", // Never do this
    secretAccessKey: "..."
  }
});

// Use IAM roles instead
const client = new S3Client({
  // Credentials loaded from IAM role
});
```

### Principle of Least Privilege
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::my-bucket/my-prefix/*"
  }]
}
```

## Code Review Security

### Check for Vulnerabilities
- SQL Injection
- XSS (Cross-Site Scripting)
- CSRF (Cross-Site Request Forgery)
- Path Traversal
- Command Injection

### Use Security Linters
```bash
# JavaScript/TypeScript
npm install --save-dev eslint-plugin-security

# Python
pip install bandit
bandit -r .

# General
npm install -g snyk
snyk test
```

## Container Security

### Don't Run as Root
```dockerfile
# Bad
USER root

# Good
RUN useradd -m appuser
USER appuser
```

### Scan Images
```bash
# Scan Docker images
docker scan my-image:latest

# Use Trivy
trivy image my-image:latest
```

## Git Security

### Sign Commits
```bash
# Configure GPG signing
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true
```

### Protect Branches
```bash
# Set up branch protection
git config branch.main.protect true
```

## Monitoring and Logging

### Log Security Events
```javascript
// Log authentication attempts
logger.info('Authentication attempt', {
  user: username,
  ip: req.ip,
  timestamp: new Date(),
  success: false
});
```

### Never Log Sensitive Data
```javascript
// Bad
logger.info('User login', { password: userPassword });

// Good
logger.info('User login', { username: user.email });
```

## Emergency Response

### If You Accidentally Commit Secrets
1. **Immediately rotate the secret**
2. Remove from history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push (coordinate with team)
4. Clean up remote references

### Security Incident Checklist
- [ ] Isolate affected systems
- [ ] Preserve logs
- [ ] Rotate all potentially compromised credentials
- [ ] Audit access logs
- [ ] Document timeline
- [ ] Implement fixes
- [ ] Post-mortem review

## Claude Code Specific

### Enable Security Hooks
```bash
# Install security essentials
claude-setup add security-essentials

# Configure limits
export MAX_FILES_PER_OPERATION=3
export MAX_LINES_PER_FILE=300
```

### Review Claude's Suggestions
Always review code changes suggested by Claude, especially:
- File permission changes
- Network requests
- Database queries
- System commands
- Authentication logic

## Additional Resources
- [OWASP Top 10](https://owasp.org/Top10/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Node.js Security Checklist](https://blog.risingstack.com/node-js-security-checklist/)