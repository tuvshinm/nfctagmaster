# NFC Attendance System Backend

A FastAPI-based backend for an NFC-based school attendance system with multi-level authentication and role-based access control.

## Features

- **Multi-level Authentication**: Student, Teacher, IT Staff, and Admin roles
- **NFC Tag Management**: Register and manage student NFC tags
- **Check-in/Out System**: Automatic attendance tracking with duty teacher association
- **Audit Logging**: Comprehensive logging of all system actions
- **REST API**: Complete RESTful API for frontend integration

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database and update connection string in `main.py`

3. Run the application:

```bash
uvicorn main:app --reload
```

## Testing

Run the comprehensive test suite:

```bash
# Using unittest
python run_tests.py

# Using pytest
pytest

# With coverage
pytest --cov=main --cov-report=html
```

### Test Coverage

The test suite covers:

- **Authentication Functions**: Password hashing, JWT token creation, user registration/login
- **Database Operations**: CRUD operations for User, Student, and AuditLog models
- **NFC Operations**: Tag registration, status checking, system scan testing
- **Student Management**: Student creation, tag assignment, status tracking
- **Check-in/Out System**: Status flipping, duty teacher association
- **Error Handling**: Authentication, validation, and edge case handling

## API Endpoints

### Authentication

- `POST /register` - User registration
- `POST /login` - User login
- `GET /status` - System status

### Teacher Level 1

- `GET /teacher/students` - Get all students
- `POST /teacher/register-tag` - Register student NFC tag
- `GET /teacher/current-duty` - Get current duty teacher
- `POST /teacher/assign-duty/{teacher_id}` - Assign duty teacher
- `GET /teacher/check-in-status` - Get student check-in status
- `GET /teacher/check-in-logs` - Get check-in/out logs

### IT Staff Level 2

- `GET /it/students` - Get all students with filtering
- `DELETE /it/students/{student_id}` - Delete student
- `GET /it/audit-logs` - Get audit logs

### Admin Level 3

- `GET /admin/users` - List all users
- `DELETE /admin/users/{user_id}` - Delete user
- `GET /admin/users/{user_id}/deactivate` - Deactivate user
- `GET /admin/users/{user_id}/activate` - Activate user

## Database Schema

### User Table

- `id`: Primary key
- `name`: Username
- `hashed_password`: Password hash
- `role`: User role (student, teacher, it_staff, admin)
- `auth_level`: Authentication level (0-3)
- `is_active`: Account status
- `assigned_duty`: Duty assignment status

### Student Table

- `id`: Primary key
- `name`: Student name
- `tid`: NFC tag ID
- `lastscan`: Last scan timestamp
- `in_school`: Current attendance status
- `schoolClass`: Class assignment
- `image`: Profile image URL

### AuditLog Table

- `id`: Primary key
- `user_id`: User who performed action
- `action`: Action performed
- `target_type`: Type of target (user, student, etc.)
- `target_id`: Target ID
- `details`: Action details
- `timestamp`: Action timestamp
- `ip_address`: Client IP
- `user_agent`: User agent

## Configuration

- Database connection: `postgresql://username:password@localhost:5432/nfctag`
- JWT secret: Generated randomly on startup
- NFC reader timeout: 20 seconds for tag registration

## Development

### Adding New Tests

1. Create test classes following the naming convention `Test*`
2. Use `setUp()` and `tearDown()` methods for test setup/teardown
3. Follow the existing test structure and naming conventions
4. Add tests for new endpoints and functionality

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test class
python -m unittest tests.test_main.TestAuthentication

# Run with verbose output
python run_tests.py -v
```
