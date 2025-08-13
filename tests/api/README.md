# Containers on the Fly - Bruno API Tests

This directory contains Bruno API tests for the Containers on the Fly application.

## Prerequisites

1. Install Bruno: https://www.usebruno.com/
2. Have the Containers on the Fly application running locally or on a test server

## Getting Started

1. Open Bruno and import this collection by selecting the `/tests/api` directory
2. Select the appropriate environment (localhost, staging, or production)
3. Update the environment variables if needed (especially for non-localhost environments)

## Test Structure

The tests are organized by access level and functionality:

```
tests/api/
├── public/           # No authentication required
│   └── app/         # Application configuration
├── auth/            # Authentication endpoints
├── user/            # User-authenticated endpoints
│   ├── profile/     # User profile management
│   └── reservations/# Reservation management
└── admin/           # Admin-only endpoints
    ├── users/       # User management
    ├── containers/  # Container management
    ├── computers/   # Computer/server management
    ├── roles/       # Role management
    └── settings/    # System settings
```

## Running Tests

### Quick Start (Localhost)

1. Start with the authentication tests to get tokens:
   - Run `auth/login.bru` (admin login)
   - Run `auth/login-user.bru` (regular user login)
   
2. These tests automatically save the authentication tokens to environment variables

3. Run other tests in any order - they will use the saved tokens

### Test Execution Order

For a comprehensive test run, follow this order:

1. **Authentication**
   - Login as admin
   - Login as regular user
   - Check token validation

2. **Public Endpoints**
   - Get application config

3. **User Endpoints**
   - Get user profile
   - Check available hardware
   - Create reservations
   - Manage reservations

4. **Admin Endpoints**
   - User management
   - Container management
   - Computer management
   - Role management
   - System settings

## Environment Variables

The following variables are used across tests:

- `root_url`: Base API URL (e.g., http://localhost:8000/api)
- `admin_email`: Admin user email (default: admin@foo.com)
- `admin_password`: Admin password (default: test)
- `user_email`: Regular user email (default: user@foo.com)
- `user_password`: Regular user password (default: test)
- `auth_token`: Current authentication token (auto-populated)
- `admin_token`: Admin authentication token (auto-populated)
- `user_token`: Regular user authentication token (auto-populated)

## Writing New Tests

When adding new tests:

1. Place them in the appropriate directory based on access level
2. Use `auth: bearer` with appropriate token variable
3. Include comprehensive test assertions
4. Follow the existing naming conventions
5. Update folder.bru metadata if adding new folders

## Common Test Patterns

### Authentication
```javascript
auth:bearer {
  token: {{admin_token}}  // or {{user_token}} for regular users
}
```

### Response Validation
```javascript
tests {
  test("Status code is 200", function() {
    expect(res.status).to.equal(200);
  });
  
  test("Response is successful", function() {
    expect(res.body).to.have.property('status');
    expect(res.body.status).to.equal('success');
  });
}
```

### Error Handling
Tests include both success and failure scenarios. Error tests check for appropriate status codes and error messages.

## Troubleshooting

1. **401 Unauthorized**: Run the login tests again to refresh tokens
2. **Connection refused**: Ensure the application is running on the expected port
3. **Test failures**: Check that test data exists (default users, containers, etc.)

## Contributing

When adding new endpoints to the application, please add corresponding Bruno tests following the existing patterns.