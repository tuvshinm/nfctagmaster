# tests/test_main.py
import unittest
import uuid
import time
from fastapi.testclient import TestClient
from main import app, engine, get_password_hash, verify_password, create_access_token, authenticate_user
from sqlmodel import Session, select
from datetime import datetime, timedelta
from main import User, Student, AuditLog, UserRole, UserCreate, UserLogin

class TestAuthentication(unittest.TestCase):
    """Test authentication functions and user management"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test123"
        hashed = get_password_hash(password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong", hashed))
        self.assertFalse(verify_password("", hashed))
        
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser", "user_id": 1, "role": "teacher"}
        token = create_access_token(data)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        
        # Test with expiration
        token_expires = create_access_token(data, expires_delta=timedelta(minutes=5))
        self.assertIsInstance(token_expires, str)
        
    def test_user_registration(self):
        """Test user registration endpoint"""
        import time
        unique_username = f"testteacher_{int(time.time())}"
        user_data = {
            "username": unique_username,
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        response = self.client.post("/register", json=user_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user_role"], UserRole.TEACHER)
        self.assertTrue("user_id" in data)
        
    def test_user_login(self):
        """Test user login endpoint"""
        # First register a user
        user_data = {
            "username": "logintest_unique",
            "password": "loginpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=user_data)
        
        # Then login
        login_data = {
            "username": "logintest_unique",
            "password": "loginpass123"
        }
        response = self.client.post("/login", json=login_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user_role"], UserRole.TEACHER)
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent_user",
            "password": "wrongpass"
        }
        response = self.client.post("/login", json=login_data)
        self.assertEqual(response.status_code, 401)
        
    def test_duplicate_registration(self):
        """Test that duplicate usernames are rejected"""
        import time
        unique_username = f"duplicate_user_{int(time.time())}"
        user_data = {
            "username": unique_username,
            "password": "pass123",
            "role": UserRole.TEACHER
        }
        # First registration should succeed
        response1 = self.client.post("/register", json=user_data)
        self.assertEqual(response1.status_code, 200)
        
        # Second registration should fail
        response2 = self.client.post("/register", json=user_data)
        self.assertEqual(response2.status_code, 400)


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations and model interactions"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_user_model_creation(self):
        """Test User model creation and properties"""
        with Session(engine) as session:
            user = User(
                name="testuser",
                hashed_password=get_password_hash("testpass"),
                role=UserRole.TEACHER,
                auth_level=1,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            self.assertIsNotNone(user.id)
            self.assertEqual(user.name, "testuser")
            self.assertEqual(user.role, UserRole.TEACHER)
            self.assertTrue(user.is_active)
            
    def test_student_model_creation(self):
        """Test Student model creation and properties"""
        with Session(engine) as session:
            student = Student(
                name="John Doe",
                tid=str(uuid.uuid4()),
                lastscan=int(time.time()),
                in_school=False
            )
            session.add(student)
            session.commit()
            session.refresh(student)
            
            self.assertIsNotNone(student.id)
            self.assertEqual(student.name, "John Doe")
            # Student model no longer has schoolClass field in database
        # self.assertEqual(student.schoolClass, "10A")
            self.assertFalse(student.in_school)
            
    def test_audit_log_creation(self):
        """Test AuditLog model creation"""
        with Session(engine) as session:
            # Create a user first
            user = User(
                name="testuser",
                hashed_password=get_password_hash("testpass"),
                role=UserRole.TEACHER
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Create audit log
            log = AuditLog(
                user_id=user.id,
                action="test_action",
                target_type="user",
                target_id=str(user.id),
                details="Test log entry",
                ip_address="127.0.0.1",
                user_agent="test-agent"
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            
            self.assertIsNotNone(log.id)
            self.assertEqual(log.user_id, user.id)
            self.assertEqual(log.action, "test_action")
            self.assertIsNotNone(log.timestamp)


class TestNFCOperations(unittest.TestCase):
    """Test NFC-related operations and tag registration"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_status_endpoint(self):
        """Test status endpoint"""
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reader_connected", data)
        
    def test_system_scan_test(self):
        """Test system scan test endpoint (requires auth)"""
        # This should fail without authentication
        response = self.client.get("/system/scan-test")
        self.assertEqual(response.status_code, 403)
        
        # Test with teacher authentication
        # First register a teacher
        teacher_data = {
            "username": "teachertest",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token and authenticate
        login_data = {
            "username": "teachertest",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test with authentication
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/system/scan-test", headers=headers)
        # This endpoint may fail if no NFC reader is available, but should not auth error
        self.assertIn(response.status_code, [200, 503])
        
    def test_teacher_current_duty(self):
        """Test current duty endpoint"""
        # Register a teacher first
        teacher_data = {
            "username": "dutyteacher",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "dutyteacher",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/teacher/current-duty", headers=headers)
        self.assertEqual(response.status_code, 200)
        
    def test_assign_duty(self):
        """Test duty assignment endpoint"""
        # Register two teachers
        for i, username in enumerate(["teacher1", "teacher2"]):
            teacher_data = {
                "username": username,
                "password": "testpass123",
                "role": UserRole.TEACHER
            }
            self.client.post("/register", json=teacher_data)
            
        # Get tokens and user IDs
        tokens = {}
        user_ids = {}
        for username in ["teacher1", "teacher2"]:
            login_data = {
                "username": username,
                "password": "testpass123"
            }
            login_response = self.client.post("/login", json=login_data)
            tokens[username] = login_response.json()["access_token"]
            user_ids[username] = login_response.json()["user_id"]
            
        # Assign duty using teacher1 to teacher2
        headers = {"Authorization": f"Bearer {tokens['teacher1']}"}
        response = self.client.post(f"/teacher/assign-duty/{user_ids['teacher2']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # Check current duty
        response = self.client.get("/teacher/current-duty", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["teacher_name"], "teacher2")


class TestStudentManagement(unittest.TestCase):
    """Test student management and registration endpoints"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_get_students_endpoint(self):
        """Test getting students endpoint"""
        # Register a teacher first
        teacher_data = {
            "username": "teachertest2",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest2",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/students", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("students", data)
        
    def test_register_tag_missing_name(self):
        """Test tag registration with missing student name"""
        # Register a teacher
        teacher_data = {
            "username": "teachertest3",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest3",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test without student name
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/teacher/register-tag", 
                                   json={"schoolClass": "10A"}, 
                                   headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Student name is required", response.json()["detail"])
        
    def test_register_tag_token_mode(self):
        """Test tag registration in token mode (no NFC required)"""
        # Register a teacher
        teacher_data = {
            "username": "teachertest4",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest4",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test token mode - should fail because no NFC reader available
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/teacher/register-tag", 
                                   json={
                                       "student_name": "Token Test Student",
                                       "schoolClass": "10B",
                                       "image": "token_student.jpg",
                                       "mode": "token"
                                   }, 
                                   headers=headers)
        # Should fail because no NFC reader available in test environment
        self.assertEqual(response.status_code, 503)


class TestCheckInOut(unittest.TestCase):
    """Test check-in/out functionality"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_check_in_status_endpoint(self):
        """Test check-in status endpoint"""
        # Register a teacher
        teacher_data = {
            "username": "teachertest5",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest5",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/teacher/check-in-status", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("students", data)
        
    def test_check_in_logs_endpoint(self):
        """Test check-in logs endpoint"""
        # Register a teacher
        teacher_data = {
            "username": "teachertest6",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest6",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/teacher/check-in-logs", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("logs", data)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_unprotected_endpoints(self):
        """Test that unprotected endpoints work without auth"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        
    def test_protected_endpoints_without_auth(self):
        """Test that protected endpoints fail without authentication"""
        protected_endpoints = [
            ("/students", "GET"),
            ("/teacher/register-tag", "POST"),
            ("/teacher/current-duty", "GET"),
            ("/system/scan-test", "GET")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint)
            else:
                response = self.client.get(endpoint)  # Default to GET
                
            self.assertEqual(response.status_code, 403)
            
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payloads"""
        # Register a teacher
        teacher_data = {
            "username": "teachertest7",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Get token
        login_data = {
            "username": "teachertest7",
            "password": "testpass123"
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Test with invalid JSON
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/teacher/register-tag", 
                                   data="invalid json", 
                                   headers=headers)
        self.assertEqual(response.status_code, 422)


class TestAdminEndpoints(unittest.TestCase):
    """Test admin-level endpoints and system management"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def setup_admin_user(self):
        """Helper method to create and authenticate an admin user"""
        # Register an admin user
        admin_data = {
            "username": f"admin_{int(time.time())}",
            "password": "adminpass123",
            "role": UserRole.ADMIN
        }
        self.client.post("/register", json=admin_data)
        
        # Login and get token
        login_data = {
            "username": admin_data["username"],
            "password": admin_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        return login_response.json()["access_token"]
        
    def setup_teacher_user(self):
        """Helper method to create and authenticate a teacher user"""
        teacher_data = {
            "username": f"teacher_{int(time.time())}",
            "password": "teacherpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        login_data = {
            "username": teacher_data["username"],
            "password": teacher_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        return login_response.json()["access_token"]
        
    def setup_student(self, session, name="Test Student", class_name="10A"):
        """Helper method to create a student"""
        student = Student(
            name=name,
            tid=str(uuid.uuid4()),
            lastscan=int(time.time()),
            in_school=False,
            schoolClass=class_name
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        return student
        
    def test_admin_users_endpoint(self):
        """Test admin users listing endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/admin/users", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("users", data)
        self.assertIsInstance(data["users"], list)
        
    def test_admin_users_endpoint_without_auth(self):
        """Test that admin users endpoint fails without authentication"""
        response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 403)
        
    def test_admin_users_endpoint_with_teacher_auth(self):
        """Test that admin users endpoint fails with teacher authentication"""
        # Register a teacher explicitly to ensure clean state
        teacher_data = {
            "username": f"teacher_test_{int(time.time())}",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        # Login and get token
        login_data = {
            "username": teacher_data["username"],
            "password": teacher_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access admin endpoint
        response = self.client.get("/admin/users", headers=headers)
        self.assertEqual(response.status_code, 403)
        
    def test_admin_system_metrics_endpoint(self):
        """Test admin system metrics endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/admin/system-metrics", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check required fields
        required_fields = [
            "total_users", "active_users", "total_checkins",
            "today_checkins", "system_uptime", "database_size",
            "nfc_reader_status"
        ]
        for field in required_fields:
            self.assertIn(field, data)
            
    def test_admin_system_config_endpoint(self):
        """Test admin system configuration endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test GET endpoint
        response = self.client.get("/admin/system-config", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check required fields
        required_fields = [
            "auto_backup_enabled", "backup_frequency", "session_timeout",
            "max_login_attempts", "nfc_scan_timeout", "enable_notifications"
        ]
        for field in required_fields:
            self.assertIn(field, data)
            
    def test_admin_system_config_update_endpoint(self):
        """Test admin system configuration update endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test PUT endpoint
        config_data = {
            "auto_backup_enabled": True,
            "backup_frequency": "weekly",
            "session_timeout": 30,
            "max_login_attempts": 5,
            "nfc_scan_timeout": 10,
            "enable_notifications": False
        }
        
        response = self.client.put("/admin/system-config",
                                 json=config_data,
                                 headers=headers)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_audit_logs_endpoint(self):
        """Test admin audit logs endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/admin/audit-logs", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("logs", data)
        self.assertIsInstance(data["logs"], list)
        
    def test_admin_generate_report_endpoint(self):
        """Test admin generate report endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.post("/admin/generate-report", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("report", data)
        
        # Check report structure
        report = data["report"]
        required_fields = [
            "generated_at", "total_users", "active_users",
            "total_students", "total_checkins"
        ]
        for field in required_fields:
            self.assertIn(field, report)
            
    def test_admin_export_data_endpoint(self):
        """Test admin export data endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.post("/admin/export-data", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data", data)
        
        # Check export structure
        export_data = data["data"]
        required_fields = ["exported_at", "users", "students", "audit_logs"]
        for field in required_fields:
            self.assertIn(field, export_data)
            
    def test_admin_create_backup_endpoint(self):
        """Test admin create backup endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.post("/admin/create-backup", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("backup", data)
        
        # Check backup structure
        backup = data["backup"]
        required_fields = ["backup_id", "created_at", "size", "status"]
        for field in required_fields:
            self.assertIn(field, backup)
            
    def test_admin_maintenance_endpoint(self):
        """Test admin maintenance endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.post("/admin/maintenance", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tasks", data)
        self.assertIsInstance(data["tasks"], list)
        
    def test_admin_emergency_shutdown_endpoint(self):
        """Test admin emergency shutdown endpoint"""
        # Setup admin user
        token = self.setup_admin_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.post("/admin/emergency-shutdown", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        
    def test_admin_user_role_update(self):
        """Test admin user role update endpoint"""
        # Setup admin and teacher users
        admin_token = self.setup_admin_user()
        teacher_token = self.setup_teacher_user()
        
        # Get teacher user ID from the setup method
        teacher_data = {
            "username": f"teacher_{int(time.time())}",
            "password": "teacherpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        login_response = self.client.post("/login", json=teacher_data)
        teacher_id = login_response.json()["user_id"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Update teacher role to admin
        response = self.client.get(f"/admin/users/{teacher_id}/role",
                                 params={"role": "admin"},
                                 headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_user_deletion(self):
        """Test admin user deletion endpoint"""
        # Setup admin and teacher users
        admin_token = self.setup_admin_user()
        teacher_token = self.setup_teacher_user()
        
        # Get teacher user ID
        login_response = self.client.post("/login", json={
            "username": f"teacher_{int(time.time())}",
            "password": "teacherpass123"
        })
        teacher_id = login_response.json()["user_id"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Delete teacher user
        response = self.client.delete(f"/admin/users/{teacher_id}",
                                    headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_user_activation(self):
        """Test admin user activation endpoint"""
        # Setup admin and teacher users
        admin_token = self.setup_admin_user()
        teacher_token = self.setup_teacher_user()
        
        # Get teacher user ID
        login_response = self.client.post("/login", json={
            "username": f"teacher_{int(time.time())}",
            "password": "teacherpass123"
        })
        teacher_id = login_response.json()["user_id"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Deactivate user first
        response = self.client.get(f"/admin/users/{teacher_id}/deactivate",
                                 headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        
        # Activate user
        response = self.client.get(f"/admin/users/{teacher_id}/activate",
                                 headers=admin_headers)
        self.assertEqual(response.status_code, 200)


class TestITStaffEndpoints(unittest.TestCase):
    """Test IT staff-level endpoints"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def setup_it_staff_user(self):
        """Helper method to create and authenticate an IT staff user"""
        it_staff_data = {
            "username": f"itstaff_{int(time.time())}",
            "password": "itpass123",
            "role": UserRole.IT_STAFF
        }
        self.client.post("/register", json=it_staff_data)
        
        login_data = {
            "username": it_staff_data["username"],
            "password": it_staff_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        return login_response.json()["access_token"]
        
    def setup_student(self, session, name="Test Student", class_name="10A"):
        """Helper method to create a student"""
        student = Student(
            name=name,
            tid=str(uuid.uuid4()),
            lastscan=int(time.time()),
            in_school=False,
            schoolClass=class_name
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        return student
        
    def test_it_students_endpoint(self):
        """Test IT staff students endpoint"""
        # Setup IT staff user
        token = self.setup_it_staff_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/students", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("students", data)
        self.assertIsInstance(data["students"], list)
        
    def test_it_students_endpoint_without_auth(self):
        """Test that IT students endpoint fails without authentication"""
        response = self.client.get("/students")
        self.assertEqual(response.status_code, 403)
        
    def test_it_students_endpoint_with_teacher_auth(self):
        """Test that IT students endpoint allows teacher authentication"""
        # Register a teacher explicitly to ensure clean state
        teacher_data = {
            "username": f"teacher_it_test_{int(time.time())}",
            "password": "testpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        login_data = {
            "username": teacher_data["username"],
            "password": teacher_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/students", headers=headers)
        self.assertEqual(response.status_code, 200)
        
    def test_it_audit_logs_endpoint(self):
        """Test IT staff audit logs endpoint"""
        # Setup IT staff user
        token = self.setup_it_staff_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/it/audit-logs", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("logs", data)
        self.assertIsInstance(data["logs"], list)
        
    def test_it_student_deletion(self):
        """Test IT staff student deletion endpoint"""
        # Setup IT staff user and create a student
        token = self.setup_it_staff_user()
        
        with Session(engine) as session:
            student = self.setup_student(session, "Delete Me Student", "10B")
            student_id = student.id
            
        it_headers = {"Authorization": f"Bearer {token}"}
        
        # Delete student
        response = self.client.delete(f"/it/students/{student_id}",
                                    headers=it_headers)
        self.assertEqual(response.status_code, 200)
        
        # Verify student is deleted
        with Session(engine) as session:
            deleted_student = session.exec(select(Student).where(Student.id == student_id)).first()
            self.assertIsNone(deleted_student)


class TestTeacherEndpoints(unittest.TestCase):
    """Test teacher-level endpoints"""
    
    def setUp(self):
        self.client = TestClient(app)
        
    def setup_teacher_user(self):
        """Helper method to create and authenticate a teacher user"""
        teacher_data = {
            "username": f"teacher_{int(time.time())}",
            "password": "teacherpass123",
            "role": UserRole.TEACHER
        }
        self.client.post("/register", json=teacher_data)
        
        login_data = {
            "username": teacher_data["username"],
            "password": teacher_data["password"]
        }
        login_response = self.client.post("/login", json=login_data)
        return login_response.json()["access_token"]
        
    def setup_student(self, session, name="Test Student", class_name="10A"):
        """Helper method to create a student"""
        student = Student(
            name=name,
            tid=str(uuid.uuid4()),
            lastscan=int(time.time()),
            in_school=False,
            schoolClass=class_name
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        return student
        
    def test_teacher_students_endpoint(self):
        """Test teacher students endpoint"""
        # Setup teacher user
        token = self.setup_teacher_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/students", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("students", data)
        self.assertIsInstance(data["students"], list)
        
    def test_teacher_check_in_status_endpoint(self):
        """Test teacher check-in status endpoint"""
        # Setup teacher user
        token = self.setup_teacher_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/teacher/check-in-status", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("students", data)
        self.assertIsInstance(data["students"], list)
        
    def test_teacher_check_in_logs_endpoint(self):
        """Test teacher check-in logs endpoint"""
        # Setup teacher user
        token = self.setup_teacher_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint
        response = self.client.get("/teacher/check-in-logs", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("logs", data)
        self.assertIsInstance(data["logs"], list)


if __name__ == '__main__':
    unittest.main()