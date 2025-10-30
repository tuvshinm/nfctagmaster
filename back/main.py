# main.py
import time
import threading
import binascii
from typing import Optional
from contextlib import asynccontextmanager
import uuid
import usb.core
import usb.util
import nfc
from ndef import TextRecord
from sqlmodel import SQLModel, Session, Field, create_engine, select
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from enum import Enum
import secrets
import hashlib
import jwt

# --- Authentication Models ---
class UserRole(str, Enum):
    TEACHER = "teacher"  # Auth Level 1 - Create/delete tokens, manage daily check-in
    IT_STAFF = "it_staff"  # Auth Level 2 - Mass operations, system management
    ADMIN = "admin"  # Auth Level 3 - Full system access

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tid: str
    name: str 
    is_active: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.TEACHER)
    auth_level: int = Field(default=1)  # 0=student, 1=teacher, 2=it_staff, 3=admin
    hashed_password: Optional[str] = Field(default=None)
    assigned_duty: Optional[bool] = Field(default=False)  # For daily "janitor" duty
class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tid: str
    name: str   
    lastscan: int
    in_school: bool
    schoolClass: str
    image: str
class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    action: str
    target_type: str  # "user", "token", "system", etc.
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: UserRole
    user_id: int

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.TEACHER
    assigned_duty: bool = False

class newUser(BaseModel):
    id: int | None = Field(default=None, primary_key=True)
    tid: str
    name: str
    lastscan: int
    in_school: bool

# --- Database Setup ---
engine = create_engine("postgresql://username:password@localhost:5432/nfctag")
SQLModel.metadata.create_all(engine)

# --- Authentication Configuration ---
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Authentication Functions ---
def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(session: Session, username: str, password: str):
    user = session.exec(select(User).where(User.name == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def log_action(session: Session, user_id: int, action: str, target_type: str, target_id: Optional[str] = None, details: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """Log user actions for audit purposes"""
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    session.add(log_entry)
    session.commit()

# --- Security ---
security = HTTPBearer()

async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        if username is None or user_id is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id, role=UserRole(role))
    except jwt.PyJWTError:
        raise credentials_exception
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == token_data.user_id)).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_auth_level(required_level: int):
    """Decorator to require specific authentication level"""
    def dependency(current_user: User = Depends(get_current_active_user)):
        if current_user.auth_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required level {required_level}, you have level {current_user.auth_level}"
            )
        return current_user
    return dependency

def require_role(required_role: UserRole):
    """Decorator to require specific role"""
    def dependency(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} required"
            )
        return current_user
    return dependency

# --- NFC and Database Globals ---
_clf: Optional[nfc.ContactlessFrontend] = None
_scan_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_clf_lock = threading.Lock()  # Prevent concurrent connect() calls

app = FastAPI()  # will be replaced by app = FastAPI(lifespan=lifespan) below

try:
    import usb1
except Exception:
    usb1 = None

import usb.core
import usb.util

device = None
LASTUUID="example"
LASTID = "example"
ACR122_VID = 0x072F
ACR122_PID = 0x2200

def reset_acr122(timeout: float = 0.6) -> bool:
    # Try to reset ACR122 using usb1 (libusb1) if available, then fallback to PyUSB.
    # Returns True if any reset attempt succeeded (or device not present but no exception),
    # False if all attempts failed.
    # 1) Try usb1 (libusb1) reset — preferred, because nfcpy uses usb1/libusb1
    if usb1 is not None:
        try:
            ctx = usb1.USBContext()
            for dev in ctx.getDeviceList(skip_on_error=True):
                try:
                    if dev.getVendorID() == ACR122_VID and dev.getProductID() == ACR122_PID:
                        handle = dev.open()
                        try:
                            # DeviceHandle.resetDevice() - resets USB device
                            handle.resetDevice()
                            # small pause to let OS re-enumerate
                            time.sleep(timeout)
                            handle.close()
                            print("usb1: device reset successfully.")
                            ctx.exit()
                            return True
                        except Exception as e:
                            try:
                                handle.close()
                            except Exception:
                                pass
                            print("usb1: reset failed:", repr(e))
                except Exception:
                    # ignore single-device errors, continue scanning
                    pass
            ctx.exit()
        except Exception as e:
            print("usb1 context/setup error:", repr(e))

    # 2) Fallback to PyUSB reset (works in many cases)
    try:
        dev = usb.core.find(idVendor=ACR122_VID, idProduct=ACR122_PID)
    except Exception as e:
        print("pyusb find error:", repr(e))
        dev = None

    if dev is None:
        print("USB device (ACR122) not found for reset (pyusb).")
    else:
        try:
            # dispose resources first
            try:
                usb.util.dispose_resources(dev)
            except Exception:
                pass
            dev.reset()
            time.sleep(timeout)
            return True
        except Exception as e:
            print("pyusb: USB rese failed:", repr(e))

    return False

def format_tag_id(tag):
    try:
        return tag.identifier.hex()
    except Exception:
        try:
            return binascii.hexlify(tag.identifier).decode()
        except Exception:
            return str(tag.identifier)


def handle_tag(tag, request: Optional[Request] = None):
    # Called when a tag is connected. Checks TextRecord content and processes check-in/out
    global LASTID, device, LASTUUID
    tid = format_tag_id(tag)
    print(f"Tag detected: id={tid}")
    
    try:
        if getattr(tag, "ndef", None):
            if tag.ndef:
                found_textrecord = False
                for record in tag.ndef.records:
                    if isinstance(record, TextRecord):
                        found_textrecord = True
                        text_content = record.text
                        print(f"Tag content: {text_content}")
                        
                        # Process check-in/out logic
                        process_nfc_scan(text_content, request)
                        
                if not found_textrecord:
                    print("No TextRecord found on tag")
            else:
                print("Tag has no NDEF records")
        else:
            print("Tag is not NDEF-compatible")
            
        if LASTID != tid:
            # if device: #This shit doesn't work at the moment because of AssertionError and shit.
            #     try:
            #         device.turn_on_led_and_buzzer()
            #     except Exception as e:
            #         print("LED/buzzer activation failed:", repr(e))
            LASTID = tid
            print("New tag detected")
    except Exception as e:
        print("Error reading NDEF:", repr(e))

def process_nfc_scan(tag_content: str, request: Optional[Request] = None):
    """Process NFC scan for check-in/out with duty teacher association"""
    try:
        with Session(engine) as session:
            # Find the user by tag content
            user = session.exec(select(Student).where(Student.tid == tag_content)).first()
            if not user:
                print(f"No user found for tag: {tag_content}")
                return
            
            # Get current duty teacher
            duty_teacher = session.exec(select(User).where(User.assigned_duty == True)).first()
            duty_teacher_name = duty_teacher.name if duty_teacher else "No duty teacher"
            duty_teacher_id = duty_teacher.id if duty_teacher else None
            
            # Determine scan type and flip in_school status
            scan_time = int(time.time())
            old_status = user.in_school
            new_status = not old_status  # Flip the status
            
            # Update user record
            user.in_school = new_status
            user.lastscan = scan_time
            session.commit()
            
            # Log the scan with duty teacher association
            scan_type = "check_in" if new_status else "check_out"
            log_action(
                session,
                user.id,
                f"{scan_type}_with_duty_teacher",
                "user",
                str(user.id),
                f"User {user.name} {scan_type} - Duty teacher: {duty_teacher_name}",
                request.client.host if request else None,
                request.headers.get("user-agent") if request else None
            )
            
            # Also log from duty teacher's perspective if available
            if duty_teacher_id:
                log_action(
                    session,
                    duty_teacher_id,
                    f"recorded_{scan_type}",
                    "user",
                    str(user.id),
                    f"Recorded {user.name} {scan_type} - Teacher on duty",
                    request.client.host if request else None,
                    request.headers.get("user-agent") if request else None
                )
            
            print(f"Processed {scan_type} for {user.name} (was {old_status}, now {new_status}) - Duty teacher: {duty_teacher_name}")
            
    except Exception as e:
        print(f"Error processing NFC scan: {repr(e)}")


def scan_loop(clf: nfc.ContactlessFrontend, stop_event: threading.Event, poll_period: float = 2.0):
    """Continuously poll for NFC tags. Uses _clf_lock to prevent concurrent access."""
    print("NFC scan loop started.")    
    while not stop_event.is_set():
        tag_found = False

        def on_connect(tag):
            nonlocal tag_found
            tag_found = True
            try:
                handle_tag(tag)
            except Exception as e:
                print("Error in on_connect handler:", repr(e))
            return False  # disconnect immediately after processing

        start = time.time()

        def terminate():
            return stop_event.is_set() or (time.time() - start) > poll_period

        acquired = _clf_lock.acquire(timeout=5.0)
        if not acquired:
            print("scan_loop: unable to acquire reader lock, skipping this cycle")
            time.sleep(0.1)
            continue

        try:
            try:
                clf.connect(rdwr={"on-connect": on_connect}, terminate=terminate)
            except Exception as e:
                print("connect() error in scan_loop:", repr(e))
        finally:
            _clf_lock.release()

        if not tag_found:
            print("none detected")

        time.sleep(0.1)

    print("NFC scan loop stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _clf, _scan_thread, _stop_event, device
    _stop_event.clear()
    reset_acr122()
    try:
        _clf = nfc.ContactlessFrontend('usb')
        print("NFC reader opened successfully at startup.")
    except Exception as e:
        print("Unable to open NFC reader at startup:", repr(e))
        _clf = None
    if device is None:
        try:
            device = nfc.clf.acr122.Device(_clf)
            print("Device instance created successfully.")
        except AssertionError as e:
            print("Failed to create Device instance:", repr(e))
            device = None
    # Background scanning thread starter
    def starter():
        global _clf
        while not _stop_event.is_set():
            if _clf is None:
                # Reset the USB device before attempting to open (helps without manual replug)
                reset_acr122()
                try:
                    _clf = nfc.ContactlessFrontend('usb')
                    print("NFC reader opened successfully.")
                except Exception as e:
                    print("Waiting for NFC reader... (open failed):", repr(e))
                    time.sleep(3)
                    continue
            try:
                scan_loop(_clf, _stop_event, poll_period=2.0)
            except Exception as e:
                print("scan_loop crashed:", repr(e))
                try:
                    if _clf:
                        _clf.close()
                except Exception:
                    pass
                _clf = None
                time.sleep(1)

    _scan_thread = threading.Thread(target=starter, daemon=True, name="nfc-scan-thread")
    _scan_thread.start()

    try:
        yield
    finally:
        print("Shutting down NFC scanner .....")
        _stop_event.set()
        if _scan_thread and _scan_thread.is_alive():
            _scan_thread.join(timeout=5.0)
        # try:
        #     if _clf:
        #         _clf.close()
        # except Exception as e:
        #     print("Error closing clf:", repr(e))
        print("Shutdown complete.")


# Assign the lifespan handler (replace previous FastAPI instance)
app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"status": "NFC scanner running"}


@app.post("/register", response_model=Token)
async def register_user(request: Request, user: UserCreate):
    """Temporary registration endpoint - DELETE AFTER CREATING ADMIN USER"""
    with Session(engine) as session:
        # Check if user already exists
        db_user = session.exec(select(User).where(User.name == user.username)).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Create new user with role-based auth level
        auth_level = 0  # Default student
        if user.role == UserRole.TEACHER:
            auth_level = 1
        elif user.role == UserRole.IT_STAFF:
            auth_level = 2
        elif user.role == UserRole.ADMIN:
            auth_level = 3
        
        hashed_password = get_password_hash(user.password)
        db_user = User(
            name=user.username,
            hashed_password=hashed_password,
            role=user.role,
            auth_level=auth_level,
            assigned_duty=user.assigned_duty
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        # Create access token with user info
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": db_user.name, 
                "user_id": db_user.id, 
                "role": db_user.role.value
            }, 
            expires_delta=access_token_expires
        )
        
        # Log registration
        log_action(
            session, 
            db_user.id, 
            "user_registered", 
            "user", 
            str(db_user.id),
            f"New user registered with role {user.role}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user_role": db_user.role,
            "user_id": db_user.id
        }

@app.post("/login", response_model=Token)
async def login_for_access_token(request: Request, form_data: UserLogin):
    with Session(engine) as session:
        user = authenticate_user(session, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.name, 
                "user_id": user.id, 
                "role": user.role.value
            }, 
            expires_delta=access_token_expires
        )
        
        # Log login
        log_action(
            session, 
            user.id, 
            "user_login", 
            "user", 
            str(user.id),
            f"User logged in from {request.client.host}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user_role": user.role,
            "user_id": user.id
        }


@app.get("/status")
def status():
    return {"reader_connected": bool(_clf is not None)}

@app.get("/system/scan-test")
async def test_scan(current_user: User = Depends(require_auth_level(1))):
    """Test endpoint to verify NFC scanning is working"""
    global _clf
    if _clf is None:
        raise HTTPException(status_code=503, detail="NFC reader not available")
    
    def test_scan_function():
        scan_result = {"detected": False, "content": None}
        
        def on_connect(tag):
            nonlocal scan_result
            try:
                if getattr(tag, "ndef", None):
                    if tag.ndef:
                        for record in tag.ndef.records:
                            if isinstance(record, TextRecord):
                                scan_result["detected"] = True
                                scan_result["content"] = record.text
                                print(f"Test scan detected: {record.text}")
                                break
                return False
            except Exception as e:
                print(f"Test scan error: {repr(e)}")
                return False

        start = time.time()

        def terminate():
            return (time.time() - start) > 5.0  # 5 second timeout for test

        acquired = _clf_lock.acquire(timeout=0.5)
        if not acquired:
            return {"error": "reader busy"}

        try:
            try:
                _clf.connect(rdwr={"on-connect": on_connect}, terminate=terminate)
            except Exception as e:
                return {"error": f"connect error: {repr(e)}"}
        finally:
            _clf_lock.release()

        return scan_result

    result = await run_in_threadpool(test_scan_function)
    return result


# --- Teacher Level 1 Endpoints ---
@app.get("/teacher/current-duty")
async def get_current_duty(current_user: User = Depends(require_auth_level(1))):
    """Get teacher currently assigned to daily duty"""
    with Session(engine) as session:
        duty_teacher = session.exec(select(User).where(User.assigned_duty == True)).first()
        if duty_teacher:
            return {
                "teacher_name": duty_teacher.name,
                "teacher_id": duty_teacher.id,
                "tid": duty_teacher.tid
            }
        return {"message": "No teacher currently on duty"}

@app.post("/teacher/assign-duty/{teacher_id}")
async def assign_duty(teacher_id: int, current_user: User = Depends(require_auth_level(1))):
    """Assign a teacher to daily duty"""
    with Session(engine) as session:
        # Remove current duty assignment
        session.exec(select(User).where(User.assigned_duty == True)).update({"assigned_duty": False})
        
        # Assign new duty
        teacher = session.exec(select(User).where(User.id == teacher_id)).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        
        teacher.assigned_duty = True
        session.commit()
        
        # Log assignment
        log_action(
            session,
            current_user.id,
            "duty_assigned",
            "user",
            str(teacher_id),
            f"Assigned duty to {teacher.name}",
            None,
            None
        )
        
        return {"message": f"Duty assigned to {teacher.name}"}

@app.get("/teacher/students")
async def get_students(current_user: User = Depends(require_auth_level(1))):
    """Get all students (teacher view)"""
    with Session(engine) as session:
        students = session.exec(select(User).where(User.role == UserRole.STUDENT)).all()
        return {"students": students}



@app.post("/teacher/register-tag")
async def register_student_tag(request: Request, student_data: dict, current_user: User = Depends(require_auth_level(1))):
    global _clf
    student_id = student_data.get("student_id")
    student_name = student_data.get("student_name")
    if not student_name:
        raise HTTPException(status_code=400, detail="Student name is required")
    def _save_student_with_tid(session: Session, name: str, tid_str: str, payload: dict):
            student = session.exec(select(Student).where(Student.name == name)).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            if payload.get("schoolClass") is not None:
                student.schoolClass = payload.get("schoolClass")
            if payload.get("image") is not None:
                student.image = payload.get("image")
            session.commit()
            student = Student(
                name=name,
                tid=tag_uuid,
                lastscan=int(time.time()),
                in_school=False,
                schoolClass=payload.get("schoolClass", ""),
                image=payload.get("image", "")
            )
            session.refresh(student)
            return student, old_tid    
    if _clf is None:
        raise HTTPException(status_code=503, detail="NFC reader not available")
    def register_tag():
        written = False
        message = None
        tag_uuid = None
        def on_connect(tag):
            nonlocal written, message, tag_uuid
            try:
                if getattr(tag, "ndef", None):
                    # Generate new UUID for the tag
                    tag_uuid = uuid.uuid4()
                    record = TextRecord(str(tag_uuid))
                    tag.ndef.records = [record]
                    written = True
                    message = f"Tag registered with UUID: {tag_uuid}"
                    with Session(engine) as session:
                        _save_student_with_tid(session, student_id, student_name, str(tag_uuid), student_data)
                    print (message)
                else:
                    message = "Tag is not NDEF-compatible"
                    print(message)
                return False
            except Exception as e:
                message = f"Registration error: {repr(e)}"
                print(message)
                return False
        start = time.time()
        def terminate():
            return (time.time() - start) > 20.0  # 20 second timeout to allow user to tap
        acquired = _clf_lock.acquire(timeout=0.5)
        if not acquired:
            return {"written": False, "reason": "reader busy"}
        try:
            try:
                _clf.connect(rdwr={"on-connect": on_connect}, terminate=terminate)
            except Exception as e:
                return {"written": False, "reason": f"connect error: {repr(e)}"}
        finally:
            _clf_lock.release()
        if written:
            return {"written": True, "reason": message, "tag_uuid": tag_uuid}
        else:
            return {"written": False, "reason": message or "no tag presented within timeout"}
    # Informational: client should show "Please press NFC tag on reader" while awaiting.
    result = await run_in_threadpool(register_tag)
    if result.get("written", False):
        tag_uuid = str(result["tag_uuid"])
        with Session(engine) as session:
            student, old_tid = _save_student_with_tid(session, student_id, student_name, tag_uuid, student_data)
            # Log tag registration
            log_action(
                session,
                current_user.id,
                "tag_registered",
                "student",
                str(student.id),
                f"Registered new tag {tag_uuid} for {student.name} (old: {old_tid})",
                request.client.host,
                request.headers.get("user-agent")
            )
            return {
                "message": "Tag registered successfully",
                "student_id": student.id,
                "student_name": student.name,
                "tag_uuid": tag_uuid,
                "mode": "write"
            }

    else:
        raise HTTPException(status_code=504, detail=result.get("reason", "registration failed"))

# --- IT Staff Level 2 Endpoints ---
@app.get("/it/students")
async def get_all_students(current_user: User = Depends(require_auth_level(2))):
    """Get all students with filtering options (IT staff view)"""
    with Session(engine) as session:
        students = session.exec(select(User).where(User.role == UserRole.STUDENT)).all()
        return {"students": students}

@app.delete("/it/students/{student_id}")
async def delete_student(student_id: int, request: Request, current_user: User = Depends(require_auth_level(2))):
    """Delete a student record (IT staff only)"""
    with Session(engine) as session:
        student = session.exec(select(User).where(User.id == student_id)).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student_name = student.name
        session.delete(student)
        session.commit()
        
        # Log deletion
        log_action(
            session,
            current_user.id,
            "student_deleted",
            "user",
            str(student_id),
            f"Deleted student {student_name}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {"message": f"Student {student_name} deleted successfully"}

@app.get("/it/audit-logs")
async def get_audit_logs(current_user: User = Depends(require_auth_level(2))):
    """Get audit logs (IT staff and admin only)"""
    with Session(engine) as session:
        logs = session.exec(select(AuditLog).order_by(AuditLog.timestamp.desc())).limit(100).all()
        return {"logs": logs}

@app.post("/it/register-tag")
async def register_student_tag_it(request: Request, student_data: dict, current_user: User = Depends(require_auth_level(2))):
    """IT staff version of tag registration with additional features"""
    return await register_student_tag(request, student_data, current_user)

@app.get("/teacher/check-in-status")
async def get_check_in_status(current_user: User = Depends(require_auth_level(1))):
    """Get current check-in status for all students"""
    with Session(engine) as session:
        students = session.exec(select(User).where(User.role == UserRole.STUDENT)).all()
        status_data = []
        
        for student in students:
            status_data.append({
                "id": student.id,
                "name": student.name,
                "tid": student.tid,
                "in_school": student.in_school,
                "last_scan": student.lastscan,
                "last_scan_time": datetime.fromtimestamp(student.lastscan).isoformat() if student.lastscan else None
            })
        
        return {"students": status_data}

@app.get("/teacher/check-in-logs")
async def get_check_in_logs(current_user: User = Depends(require_auth_level(1))):
    """Get recent check-in/out logs"""
    with Session(engine) as session:
        # Get logs for check-in/out actions with duty teacher association
        logs = session.exec(
            select(AuditLog)
            .where(AuditLog.action.in_(["check_in_with_duty_teacher", "check_out_with_duty_teacher"]))
            .order_by(AuditLog.timestamp.desc())
            .limit(50)
        ).all()
        
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
                "ip_address": log.ip_address
            })
        
        return {"logs": log_data}

# --- Admin Level 3 Endpoints ---
@app.get("/admin/users")
async def list_users(current_user: User = Depends(require_auth_level(3))):
    """List all users (admin only)"""
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        return {"users": users}

@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, request: Request, current_user: User = Depends(require_auth_level(3))):
    """Delete any user (admin only)"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_name = user.name
        session.delete(user)
        session.commit()
        
        # Log deletion
        log_action(
            session,
            current_user.id,
            "user_deleted",
            "user",
            str(user_id),
            f"Deleted user {user_name}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {"message": f"User {user_name} deleted successfully"}

@app.get("/admin/users/{user_id}/deactivate")
async def deactivate_user(user_id: int, request: Request, current_user: User = Depends(require_auth_level(3))):
    """Deactivate user (admin only)"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_active = False
        session.commit()
        
        # Log deactivation
        log_action(
            session,
            current_user.id,
            "user_deactivated",
            "user",
            str(user_id),
            f"Deactivated user {user.name}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {"message": f"User {user.name} deactivated successfully"}

@app.get("/admin/users/{user_id}/activate")
async def activate_user(user_id: int, request: Request, current_user: User = Depends(require_auth_level(3))):
    """Activate user (admin only)"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_active = True
        session.commit()
        
        # Log activation
        log_action(
            session,
            current_user.id,
            "user_activated",
            "user",
            str(user_id),
            f"Activated user {user.name}",
            request.client.host,
            request.headers.get("user-agent")
        )
        
        return {"message": f"User {user.name} activated successfully"}

@app.get("/write/{string}")
async def write_item(string: str, current_user: User = Depends(get_current_active_user)):
    """
    Waits up to 10 seconds for a tag, then writes a TextRecord containing the 'string'.
    Returns JSON: {"written": True/False, "reason": "..."
    """
    global _clf
    if _clf is None:
        raise HTTPException(status_code=503, detail="NFC reader not available")

    def write_connect():
        written = False
        message = None

        def on_connect(tag):
            nonlocal written, message
            try:
                if getattr(tag, "ndef", None):
                    record = TextRecord(string)
                    tag.ndef.records = [record]
                    written = True
                    message = f"Tag written with TextRecord: {string}"
                    print(message)
                else:
                    message = "Tag is not NDEF-compatible"
                    print(message)
                return False
            except Exception as e:
                message = f"Write error: {repr(e)}"
                print(message)
                return False

        start = time.time()

        def terminate():
            return (time.time() - start) > 10.0  # 10 second timeout

        acquired = _clf_lock.acquire(timeout=0.5)
        if not acquired:
            return {"written": False, "reason": "reader busy"}

        try:
            try:
                _clf.connect(rdwr={"on-connect": on_connect}, terminate=terminate)
            except Exception as e:
                return {"written": False, "reason": f"connect error: {repr(e)}"}
        finally:
            _clf_lock.release()

        if written:
            return {"written": True, "reason": message}
        else:
            return {"written": False, "reason": message or "no tag presented within timeout"}

    result = await run_in_threadpool(write_connect)
    if not result.get("written", False):
        raise HTTPException(status_code=504, detail=result.get("reason", "write failed"))
    return result

@app.post("/newTag")
async def write_item(newTag: newUser, current_user: User = Depends(require_auth_level(1))):
    """Adapted endpoint for teachers and above to register new NFC tags"""
    global _clf
    if _clf is None:
        raise HTTPException(status_code=503, detail="NFC reader not available")
    
    def write_connect():
        written = False
        message = None
        new_uuid = None
        
        def on_connect(tag):
            nonlocal written, message, new_uuid
            try:
                if getattr(tag, "ndef", None):
                    if tag.ndef:
                        # Generate new UUID for the tag
                        new_uuid = uuid.uuid4()
                        
                        # Write the UUID to the tag
                        record = TextRecord(str(new_uuid))
                        tag.ndef.records = [record]
                        
                        written = True
                        message = f"Tag registered with UUID: {new_uuid}"
                        print(message)
                    else:
                        message = "Tag has no NDEF records"
                        print(message)
                else:
                    message = "Tag is not NDEF-compatible"
                    print(message)
                return False
            except Exception as e:
                message = f"Registration error: {repr(e)}"
                print(message)
                return False

        start = time.time()

        def terminate():
            return (time.time() - start) > 10.0  # 10 second timeout

        acquired = _clf_lock.acquire(timeout=0.5)
        if not acquired:
            return {"written": False, "reason": "reader busy"}

        try:
            try:
                _clf.connect(rdwr={"on-connect": on_connect}, terminate=terminate)
            except Exception as e:
                return {"written": False, "reason": f"connect error: {repr(e)}"}
        finally:
            _clf_lock.release()

        if written:
            return {"written": True, "reason": message, "tag_uuid": new_uuid}
        else:
            return {"written": False, "reason": message or "no tag presented within timeout"}

    result = await run_in_threadpool(write_connect)
    
    if result.get("written", False):
        # Update user record with new tag
        with Session(engine) as session:
            # Check if user already exists
            existing_user = session.exec(select(Student).where(Student.id == newTag.id)).first()
            if not existing_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            old_tid = existing_user.tid
            existing_user.tid = str(result["tag_uuid"])
            existing_user.lastscan = int(time.time())
            session.commit()
            
            # Log tag registration
            log_action(
                session,
                current_user.id,
                "tag_registered",
                "user",
                str(newTag.id),
                f"Registered new tag {result['tag_uuid']} for {existing_user.name} (old: {old_tid})",
                None,
                None
            )
            
            return {
                "message": "Tag registered successfully",
                "user_id": newTag.id,
                "user_name": existing_user.name,
                "tag_uuid": result["tag_uuid"]
            }
    else:
        raise HTTPException(status_code=504, detail=result.get("reason", "registration failed"))