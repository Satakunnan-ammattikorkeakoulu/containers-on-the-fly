/**
 * Default legal document templates for privacy policy and terms of service.
 * Templates use {{ORGANIZATION_NAME}} and {{CONTACT_EMAIL}} placeholders
 * that are replaced with actual values when loaded in the admin panel.
 * @module legalTemplates
 */

export const privacyPolicyTemplate = `# Privacy Policy

**{{ORGANIZATION_NAME}}** operates the container reservation platform ("the Service"). This privacy policy explains what personal data we collect, why we collect it, how long we keep it, and what rights you have.

## 1. Data Controller

The data controller is **{{ORGANIZATION_NAME}}**. For questions about data protection, contact us at **{{CONTACT_EMAIL}}**.

## 2. Personal Data We Collect

### Account Information
- **Email address** (required) — used as your unique identifier and for sending reservation notifications
- **Display name** (optional) — shown in the interface for personalization
- **Password** — stored as a salted cryptographic hash, never in plain text. If your organization uses Active Directory (AD/LDAP) for authentication, your password is never stored in this system — it is only verified against the directory server at login time
- **SSH public key** (optional) — if you provide one for passwordless access to containers

### Activity Data
- **Audit log entries** — records of your logins, reservation actions, and profile changes, including the IP address of the device you used
- **Reservation records** — what containers you reserved, when, and for how long
- **Container usage data** — start/stop times, assigned ports, and error messages related to your containers

### Authentication Data (if LDAP is enabled)
If the Service is connected to an organizational directory (LDAP/Active Directory), your email and display name may also be retrieved from that directory when you log in.

### Session Data
- **Authentication token** — a randomly generated session token stored in your browser's local storage to keep you logged in. No tracking cookies are used.

## 3. Why We Process Your Data

| Data | Purpose | Legal Basis |
|------|---------|-------------|
| Email, password | Authentication and account identification | Legitimate interest (service operation) |
| Display name | Personalization of the interface | Legitimate interest |
| SSH public key | Secure access to containers | Legitimate interest |
| IP address, audit logs | Security monitoring and abuse prevention | Legitimate interest |
| Reservation records | Service delivery and resource management | Legitimate interest |
| Session token | Maintaining your login session | Legitimate interest |

## 4. Data Retention

- **Audit log entries**: Automatically deleted after a configured retention period (default: 180 days). Administrators can adjust this period.
- **Account data**: Kept for the duration of your account. When your account is removed, all personal data is anonymized (see Section 6).
- **Reservation records**: Kept for historical reporting. Personal details are cleared when your account is anonymized.
- **Session tokens**: Cleared on logout or after the session timeout period.

## 5. Data Sharing

This is a **self-hosted platform**. Your personal data is not shared with third parties, advertising networks, or analytics services. All data remains on infrastructure operated by {{ORGANIZATION_NAME}}.

## 6. Your Rights Under GDPR

You have the following rights regarding your personal data:

- **Right of access** — You can request a summary of the personal data we hold about you. Contact {{CONTACT_EMAIL}}.
- **Right to rectification** — You can update your display name and SSH public key through your profile page. For other corrections, contact us.
- **Right to erasure** — You can request that your account be anonymized. This replaces your email and name with anonymized values, clears your SSH key, passwords, and audit log details, and removes your role assignments and access list entries. Contact an administrator or {{CONTACT_EMAIL}}.
- **Right to restriction of processing** — Contact {{CONTACT_EMAIL}} to request processing restrictions.
- **Right to data portability** — Contact {{CONTACT_EMAIL}} to request an export of your data.
- **Right to object** — Contact {{CONTACT_EMAIL}} to object to processing based on legitimate interest.

## 7. Data Security

We protect your data with the following measures:

- Passwords are hashed using PBKDF2-HMAC-SHA256 with a unique salt per user
- All connections are encrypted with HTTPS
- Access to the admin interface is restricted by role-based access control
- Audit logging tracks administrative actions for accountability

## 8. Minors

If you are under the age of 16, your parent or legal guardian should be aware that you are using this Service and the data it collects. If your organization requires parental consent for users under a certain age, please follow your organization's policy.

## 9. Changes to This Policy

We may update this privacy policy from time to time. Changes will be reflected on this page with an updated date.

*Last updated: {{DATE}}*
`

export const termsOfServiceTemplate = `# Terms of Service

These terms govern your use of the container reservation platform ("the Service") operated by **{{ORGANIZATION_NAME}}**.

## 1. Service Description

The Service provides access to Docker containers with configurable hardware resources (CPU, GPU, memory) for a reserved time period. Users can reserve, start, stop, and connect to containers via SSH.

## 2. Account and Access

- Access to the Service is managed by {{ORGANIZATION_NAME}}. You may only use the account assigned to you.
- You are responsible for keeping your login credentials and SSH keys secure. Do not share them with others.
- {{ORGANIZATION_NAME}} may revoke access at any time for violations of these terms.

## 3. Acceptable Use

When using the Service, you agree to:

- Use containers only for purposes authorized by {{ORGANIZATION_NAME}}
- Not attempt to access containers or accounts belonging to other users
- Not use containers for cryptocurrency mining, illegal activities, or any purpose that violates applicable laws
- Not attempt to circumvent resource limits, port restrictions, or security controls
- Not store sensitive personal data (e.g. health records, financial data) in containers unless explicitly authorized
- Respect the hardware resources allocated to your reservation — do not attempt to consume resources beyond your allocation

## 4. Resource Management

- Containers are available for the duration of your reservation. When a reservation ends, the container and all data inside it are deleted.
- Low-priority reservations may be temporarily paused if resources are needed for higher-priority work.
- Save any important work before your reservation expires. {{ORGANIZATION_NAME}} is not responsible for data loss when containers are removed.

## 5. Service Availability

The Service is provided on a best-effort basis. {{ORGANIZATION_NAME}} does not guarantee:

- Uninterrupted availability of the Service
- Specific hardware availability at any given time
- Preservation of data within containers beyond the reservation period

## 6. Privacy

Your use of the Service is subject to our Privacy Policy, which describes what personal data is collected and how it is processed.

## 7. Limitation of Liability

To the maximum extent permitted by law, {{ORGANIZATION_NAME}} is not liable for:

- Loss of data stored in containers
- Service interruptions or downtime
- Any indirect, incidental, or consequential damages arising from use of the Service

## 8. Changes to These Terms

{{ORGANIZATION_NAME}} may update these terms at any time. Continued use of the Service after changes constitutes acceptance of the updated terms.

## 9. Governing Law

These terms are governed by the laws applicable in the jurisdiction of {{ORGANIZATION_NAME}}.

## 10. Contact

For questions about these terms, contact **{{CONTACT_EMAIL}}**.

*Last updated: {{DATE}}*
`

/**
 * Encode a string as HTML entities to obscure it from spam scrapers.
 * @param {string} str - The string to encode.
 * @returns {string} HTML entity encoded string.
 */
function obfuscateEmail(str) {
  return str.split('').map(c => `&#${c.charCodeAt(0)};`).join('')
}

/**
 * Replace template placeholders with actual values.
 * @param {string} template - The template string with {{PLACEHOLDER}} markers.
 * @param {string} organizationName - Organization name to substitute.
 * @param {string} contactEmail - Contact email to substitute.
 * @param {string} [lastUpdated] - ISO timestamp of last save, formatted as a readable date.
 * @returns {string} Template with placeholders replaced (or kept if values are empty).
 */
export function fillTemplate(template, organizationName, contactEmail, lastUpdated) {
  let result = template
  if (organizationName) {
    result = result.replace(/\{\{ORGANIZATION_NAME\}\}/g, organizationName)
  }
  if (contactEmail) {
    result = result.replace(/\{\{CONTACT_EMAIL\}\}/g, obfuscateEmail(contactEmail))
  }
  if (lastUpdated) {
    const date = new Date(lastUpdated)
    const formatted = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    result = result.replace(/\{\{DATE\}\}/g, formatted)
  }
  return result
}
