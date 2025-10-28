# main.py
import time
import threading
import binascii
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
import uuid
import usb.core
import usb.util
import nfc
from ndef import TextRecord, UriRecord
from sqlmodel import SQLModel, Session, Field, create_engine, select
from pydantic import BaseModel
# --- your SQLModel (unchanged) ---
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tid: str
    name: str   
    lastscan: int
    in_school: bool
class newUser(BaseModel):
    id: int | None = Field(default=None, primary_key=True)
    tid: str
    name: str
    lastscan: int
    in_school: bool
engine = create_engine("postgresql://username:password@localhost:5432/nfctag")
SQLModel.metadata.create_all(engine)
# Globals
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
    """
    Try to reset ACR122 using usb1 (libusb1) if available, then fallback to PyUSB.
    Returns True if any reset attempt succeeded (or device not present but no exception),
    False if all attempts failed.
    """
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


def handle_tag(tag):
    # Called when a tag is connected. Checks TextRecord content and prints it.
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
                        print(text_content)
                        
                if not found_textrecord:
                    print("No TextRecord found on tag")
            else:
                print("Tag has no NDEF records")
        if LASTID != tid:
            # if device: #This shit doesn't work at the moment because of AssertionError and shit.
            #     try:
            #         device.turn_on_led_and_buzzer()
            #     except Exception as e:
            #         print("LED/buzzer activation failed:", repr(e))
            LASTID = tid
            # Create a session here too
            with Session(engine) as session:
                statement = select(User).where(User.tid == text_content)
                first = session.exec(statement).first()
                print(first)
            print("new")
    except Exception as e:
        print("Error reading NDEF:", repr(e))


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


@app.get("/status")
def status():
    return {"reader_connected": bool(_clf is not None)}


@app.get("/write/{string}")
async def write_item(string: str):
    """
    Waits up to 10 seconds for a tag, then writes a TextRecord containing the 'string'.
    Returns JSON: {"written": True/False, "reason": "..."}
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
async def write_item(newTag: User):
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
                    if tag.ndef:
                        for record in tag.ndef.records:
                            if isinstance(record, TextRecord):
                                text_content = record.text
                                with Session(engine) as session:
                                    statement = select(User).where(User.tid == text_content)
                                    hero = session.exec(statement).first()
                                    if hero == None:
                                        newUuid = uuid.uuid4()
                                        record = TextRecord(str(newUuid))
                                        tag.ndef.records = [record]
                                        newTag.tid = newUuid
                                        t = time.time()
                                        newTag.lastscan = int(t)
                                        answer = session.add(newTag)
                                        session.commit()
                                        written = True
                                        print(f"added {answer}")
                                            
                    else:
                        print("Tag has no NDEF records")
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