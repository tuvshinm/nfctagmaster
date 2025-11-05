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
        response = self.client.get("/teacher/students", headers=headers)
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
            ("/teacher/students", "GET"),
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


if __name__ == '__main__':
    unittest.main()