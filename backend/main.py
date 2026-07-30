"""
Quadriplegic Telemedicine Platform - FastAPI Backend
Accessibility-first API with voice support and assistive technology integration
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uvicorn
import os
from enum import Enum
from sqlalchemy.orm import Session

# Import services
from backend.app.services.triage_service import analyze_patient_symptoms
from backend.app.services.queue_service import add_patient_to_queue, virtual_queue

# Persistence + auth
from backend.app.db import get_db, init_db
from backend.app.models.database import (
    Patient, Appointment, AuditLog,
    DisabilityType as DBDisabilityType,
    AssistiveTech as DBAssistiveTech,
    AppointmentStatus,
)
from backend.app.core.security import (
    get_password_hash, verify_password, create_access_token, get_current_patient,
)

# Initialize FastAPI app
app = FastAPI(
    title="Quadriplegic Telemedicine API",
    description="""
    Accessibility-first telemedicine platform for quadriplegic patients.

    Key Features:
    - Voice-first symptom reporting
    - AI triage with SCI-specific complication detection
    - Virtual queue with two-layer priority (clinical + accessibility)
    - Automatic teleconsult for long waits
    - Caregiver proxy mode
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - restricted to an explicit allowlist. Override in production via the
# ALLOWED_ORIGINS env var (comma-separated). Native mobile requests (Expo Go)
# send no Origin header and are unaffected; this guards the web build + docs.
_default_origins = "http://localhost:8081,http://localhost:19006,http://127.0.0.1:8081"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Create tables on startup (idempotent). Uses SQLite by default; set DATABASE_URL
# for Postgres. See backend/app/db.py.
@app.on_event("startup")
def _startup():
    init_db()

security = HTTPBearer()

# ============= ENUMS =============

class DisabilityType(str, Enum):
    QUADRIPLEGIA = "quadriplegia"
    PARAPLEGIA = "paraplegia"
    ALS = "als"
    MS = "ms"
    OTHER = "other"

class AssistiveTech(str, Enum):
    NONE = "none"
    EYE_TRACKING = "eye_tracking"
    HEAD_MOUSE = "head_mouse"
    SIP_PUFF = "sip_puff"
    SWITCH = "switch"
    VOICE = "voice"
    CAREGIVER_PROXY = "caregiver_proxy"

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ============= PYDANTIC MODELS =============

class PatientRegistration(BaseModel):
    """Patient registration with accessibility profile."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_primary: str = Field(..., min_length=10)
    phone_emergency: Optional[str] = None

    # Disability info
    disability_type: DisabilityType = DisabilityType.QUADRIPLEGIA
    disability_description: Optional[str] = None

    # Assistive technology
    primary_assistive_tech: AssistiveTech = AssistiveTech.VOICE
    secondary_assistive_tech: Optional[AssistiveTech] = None

    # Communication
    preferred_communication: str = "voice"  # voice, text, video, caregiver
    communication_notes: Optional[str] = None

    # Caregiver
    has_caregiver: bool = False
    caregiver_name: Optional[str] = None
    caregiver_phone: Optional[str] = None
    caregiver_can_schedule: bool = False

    # Address
    address_line1: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SymptomReport(BaseModel):
    """Symptom report via text or voice."""
    patient_id: str
    symptoms_text: str = Field(..., min_length=10, description="Describe your symptoms")
    voice_recording_url: Optional[str] = None
    pain_level: Optional[int] = Field(None, ge=0, le=10)
    duration_hours: Optional[int] = None

class TriageResponse(BaseModel):
    """AI Triage result."""
    priority: str
    confidence: float
    recommended_action: str
    urgency_minutes: Optional[int]
    reasoning: str
    matched_symptoms: List[str]
    potential_conditions: List[Dict]

class QueueTicketRequest(BaseModel):
    """Request to join virtual queue."""
    patient_id: str
    patient_name: str
    priority: str  # low, medium, high, critical
    is_pwd: bool = True
    preferred_time: Optional[datetime] = None

class QueueStatusResponse(BaseModel):
    """Queue status with position and ETA."""
    ticket_id: str
    position: int
    total_waiting: int
    estimated_wait_minutes: int
    eta: Optional[str]
    teleconsult_offered: bool
    message: str

class AppointmentRequest(BaseModel):
    """Schedule appointment after triage."""
    patient_id: str
    triage_id: str
    appointment_type: str  # teleconsult, hospital, home_visit
    preferred_date: Optional[datetime] = None
    special_needs: Optional[List[str]] = []

class VoiceCommand(BaseModel):
    """Voice command processing."""
    patient_id: str
    audio_data: str  # Base64 encoded audio
    command_type: str  # "symptom_report", "queue_status", "emergency"

# ============= API ENDPOINTS =============

@app.get("/")
def root():
    """API root with system status."""
    return {
        "service": "Quadriplegic Telemedicine Platform",
        "version": "1.0.0",
        "status": "operational",
        "accessibility_features": [
            "voice_first_interface",
            "eye_tracking_support",
            "switch_access_compatible",
            "caregiver_proxy_mode",
            "large_touch_targets",
            "high_contrast_mode"
        ],
        "endpoints": {
            "patient_registration": "/patients/register",
            "symptom_report": "/triage/report",
            "queue_join": "/queue/join",
            "queue_status": "/queue/status/{ticket_id}",
            "voice_command": "/voice/command"
        }
    }

# --- Enum mapping between the API's tokens and the DB enum values ---
_TECH_APP_TO_DB = {
    "none": DBAssistiveTech.NONE,
    "eye_tracking": DBAssistiveTech.EYE_TRACKING,
    "head_mouse": DBAssistiveTech.HEAD_MOUSE,
    "sip_puff": DBAssistiveTech.SIP_PUFF,
    "switch": DBAssistiveTech.SWITCH,
    "voice": DBAssistiveTech.VOICE,
    "caregiver_proxy": DBAssistiveTech.CAREGIVER_PROXY,
}
_DISABILITY_APP_TO_DB = {
    "quadriplegia": DBDisabilityType.QUADRIPLEGIA,
    "paraplegia": DBDisabilityType.PARAPLEGIA,
    "als": DBDisabilityType.ALS,
    "ms": DBDisabilityType.MS,
    "other": DBDisabilityType.OTHER,
}


def _apply_registration(db: Session, patient: "PatientRegistration", password: Optional[str] = None) -> Patient:
    """Create + persist a Patient row from a registration payload."""
    row = Patient(
        first_name=patient.first_name,
        last_name=patient.last_name,
        phone_primary=patient.phone_primary,
        phone_emergency=patient.phone_emergency,
        disability_type=_DISABILITY_APP_TO_DB.get(
            getattr(patient.disability_type, "value", patient.disability_type), DBDisabilityType.QUADRIPLEGIA),
        disability_description=patient.disability_description,
        primary_assistive_tech=_TECH_APP_TO_DB.get(
            getattr(patient.primary_assistive_tech, "value", patient.primary_assistive_tech), DBAssistiveTech.VOICE),
        has_caregiver=patient.has_caregiver,
        caregiver_name=patient.caregiver_name,
        caregiver_phone=patient.caregiver_phone,
        caregiver_can_schedule=patient.caregiver_can_schedule,
        address_line1=patient.address_line1,
        city=patient.city,
        region=patient.region,
        latitude=patient.latitude,
        longitude=patient.longitude,
    )
    if password:
        row.password_hash = get_password_hash(password)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post("/patients/register")
def register_patient(patient: PatientRegistration, db: Session = Depends(get_db)):
    """
    Register new patient with accessibility profile.
    Now actually persists the patient to the database.
    """
    row = _apply_registration(db, patient)
    return {
        "success": True,
        "patient_id": row.uuid,
        "message": f"Welcome {row.first_name}. Your accessibility profile has been saved.",
        "accessibility_settings": {
            "primary_tech": patient.primary_assistive_tech,
            "ui_recommendations": _get_ui_recommendations(patient.primary_assistive_tech)
        }
    }

def _get_ui_recommendations(tech: AssistiveTech) -> Dict:
    """Generate UI recommendations based on assistive technology."""
    recommendations = {
        AssistiveTech.EYE_TRACKING: {
            "click_target_size": "80x80px",
            "dwell_time_ms": 1500,
            "layout": "sparse",
            "gaze_reactive": True
        },
        AssistiveTech.HEAD_MOUSE: {
            "click_target_size": "60x60px",
            "sticky_buttons": True,
            "motion_smoothing": True
        },
        AssistiveTech.SIP_PUFF: {
            "scanning_speed": "medium",
            "binary_input_mode": True,
            "simplified_interface": True
        },
        AssistiveTech.VOICE: {
            "voice_activation": True,
            "continuous_listening": False,
            "wake_word": "Hey Doc"
        },
        AssistiveTech.SWITCH: {
            "scanning_mode": "auto",
            "scan_speed_ms": 2000,
            "switch_count": 1
        },
        AssistiveTech.CAREGIVER_PROXY: {
            "caregiver_mode": True,
            "patient_consent_required": True,
            "audit_logging": True
        }
    }
    return recommendations.get(tech, {})

# ============= AUTH =============

class AuthRegister(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=9)
    password: str = Field(..., min_length=4)
    preferred_language: str = "en"


class AuthLogin(BaseModel):
    phone: str
    password: str


@app.post("/auth/register")
def auth_register(body: AuthRegister, db: Session = Depends(get_db)):
    """Register a patient with a password and issue an access token."""
    existing = db.query(Patient).filter(Patient.phone_primary == body.phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")
    parts = body.name.strip().split()
    first = parts[0] if parts else "Friend"
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    row = Patient(
        first_name=first,
        last_name=last,
        phone_primary=body.phone,
        preferred_language=(body.preferred_language or "en"),
        password_hash=get_password_hash(body.password),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "access_token": create_access_token(row.uuid),
        "token_type": "bearer",
        "patient": row.to_api_dict(),
    }


@app.post("/auth/login")
def auth_login(body: AuthLogin, db: Session = Depends(get_db)):
    """Authenticate by phone + password and issue an access token."""
    row = db.query(Patient).filter(Patient.phone_primary == body.phone).first()
    if not row or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    row.last_login = datetime.utcnow()
    db.commit()
    return {
        "access_token": create_access_token(row.uuid),
        "token_type": "bearer",
        "patient": row.to_api_dict(),
    }


@app.get("/auth/me")
def auth_me(current: Patient = Depends(get_current_patient)):
    """Return the authenticated patient's profile."""
    return current.to_api_dict()


# ============= APPOINTMENTS =============

_PROVIDER_DEFAULT = {
    "teleconsult": "AfyaConnect teleconsult",
    "hospital": "Hospital visit",
    "home_visit": "Home visit nurse",
}


def _appt_to_api(a: Appointment) -> Dict:
    """Serialize to the shape the mobile AppointmentsScreen expects."""
    if a.doctor is not None:
        provider = f"Dr. {a.doctor.first_name} {a.doctor.last_name}"
    else:
        provider = a.notes or _PROVIDER_DEFAULT.get(a.appointment_type, "Care team")
    return {
        "id": a.uuid,
        "type": a.appointment_type,
        "provider": provider,
        "starts_at": a.scheduled_time.isoformat() if a.scheduled_time else None,
        "joinable": a.appointment_type == "teleconsult",
    }


class AppointmentCreate(BaseModel):
    appointment_type: str = "teleconsult"  # teleconsult, hospital, home_visit
    scheduled_time: Optional[datetime] = None
    provider: Optional[str] = None


@app.get("/appointments")
def list_appointments(current: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    """List the authenticated patient's upcoming appointments."""
    rows = (
        db.query(Appointment)
        .filter(Appointment.patient_id == current.id)
        .order_by(Appointment.scheduled_time.asc())
        .all()
    )
    return {"appointments": [_appt_to_api(a) for a in rows]}


@app.post("/appointments")
def create_appointment(
    body: AppointmentCreate,
    current: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """Book an appointment for the authenticated patient."""
    when = body.scheduled_time or (datetime.utcnow() + timedelta(hours=2))
    a = Appointment(
        patient_id=current.id,
        appointment_type=body.appointment_type,
        scheduled_time=when,
        status=AppointmentStatus.SCHEDULED,
        notes=body.provider,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _appt_to_api(a)


# ============= AUDIT LOG (caregiver actions) =============

class AuditLogIn(BaseModel):
    caregiver_id: Optional[str] = None
    patient_id: Optional[str] = None
    action: str
    meta: Optional[Dict] = {}


@app.post("/audit/log")
def write_audit_log(body: AuditLogIn, db: Session = Depends(get_db)):
    """Persist a caregiver action to the audit log."""
    entry = AuditLog(
        user_id=body.caregiver_id,
        user_type="caregiver",
        action=body.action,
        resource_type="patient",
        resource_id=body.patient_id,
        details=body.meta or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "logged": True,
        "entry": {
            "caregiver_id": body.caregiver_id,
            "patient_id": body.patient_id,
            "action": body.action,
            "meta": body.meta or {},
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        },
    }


@app.post("/triage/report", response_model=TriageResponse)
def report_symptoms(report: SymptomReport):
    """
    Submit symptom report for AI triage.
    Supports text or voice input (voice transcribed automatically).
    """
    try:
        # Analyze symptoms
        result = analyze_patient_symptoms(
            symptoms=report.symptoms_text,
            disability_type="quadriplegia",  # Would lookup from patient record
            is_pwd=True
        )

        return TriageResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage analysis failed: {str(e)}")

@app.post("/queue/join")
def join_queue(request: QueueTicketRequest):
    """
    Join virtual queue with priority-based positioning.

    Two-layer priority:
    1. Clinical urgency (CRITICAL > HIGH > MEDIUM > LOW)
    2. Accessibility (PWDs prioritized within same clinical tier)
    """
    try:
        result = add_patient_to_queue(
            patient_id=request.patient_id,
            patient_name=request.patient_name,
            priority=request.priority,
            is_pwd=request.is_pwd
        )

        # Check if teleconsult should be offered
        if result["estimated_wait_minutes"] > 45 and request.priority in ["low", "medium"]:
            result["teleconsult_recommended"] = True
            result["message"] += " Teleconsult available to avoid long wait."

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue join failed: {str(e)}")

@app.get("/queue/status/{ticket_id}")
def get_queue_status(ticket_id: str):
    """Get current position and ETA in queue."""
    status = virtual_queue.get_queue_status(ticket_id)

    if "your_ticket" not in status:
        raise HTTPException(status_code=404, detail="Ticket not found")

    your_ticket = status["your_ticket"]

    return {
        "ticket_id": ticket_id,
        "position": your_ticket["position"],
        "total_waiting": status["total_waiting"],
        "estimated_wait_minutes": your_ticket["estimated_wait_minutes"],
        "eta": your_ticket["eta"],
        "clinical_priority": your_ticket["clinical_priority"],
        "is_pwd": your_ticket["is_pwd"],
        "teleconsult_offered": your_ticket["teleconsult_offered"],
        "message": f"You are position {your_ticket['position']} of {status['total_waiting']}. "
                   f"Estimated wait: {your_ticket['estimated_wait_minutes']} minutes."
    }

@app.post("/queue/teleconsult/accept/{ticket_id}")
def accept_teleconsult(ticket_id: str):
    """
    Accept teleconsult offer to avoid physical queue wait.
    Removes patient from physical queue, schedules video consultation.
    """
    success = virtual_queue.accept_teleconsult(ticket_id)

    if success:
        return {
            "success": True,
            "message": "Teleconsult accepted. You will receive a video call link via SMS.",
            "next_steps": [
                "Check SMS for meeting link",
                "Test camera and microphone",
                "Have medications list ready",
                "Caregiver can join if needed"
            ]
        }
    else:
        raise HTTPException(status_code=400, detail="Cannot accept teleconsult for this ticket")

@app.post("/voice/command")
def process_voice_command(command: VoiceCommand):
    """
    Process voice command for hands-free operation.
    Supports: symptom reporting, queue status, emergency alerts
    """
    # In production: Use Whisper API for transcription
    # For MVP: Simulated response

    if command.command_type == "emergency":
        return {
            "action": "emergency_alert",
            "message": "Emergency services notified. Stay calm, help is coming.",
            "emergency_contacts_called": True,
            "ambulance_dispatched": False  # Would assess based on location
        }

    elif command.command_type == "queue_status":
        return {
            "action": "queue_status_voice",
            "spoken_response": "You are position 3 in queue. Estimated wait: 25 minutes. "
                               "Would you like me to schedule a teleconsult instead?",
            "options": ["yes_teleconsult", "no_wait", "caregiver_help"]
        }

    elif command.command_type == "symptom_report":
        return {
            "action": "symptom_captured",
            "message": "Symptoms recorded. Analyzing now...",
            "transcription": "Patient reports chest pain and difficulty breathing",
            "triage_result": {
                "priority": "CRITICAL",
                "action": "immediate_hospital"
            }
        }

    return {"action": "unknown", "message": "Command not recognized"}

@app.get("/accessibility/fairness-metrics")
def get_fairness_metrics():
    """
    Get queue fairness metrics to ensure PWDs are accommodated
    without disadvantaging other patients.
    """
    metrics = virtual_queue.get_fairness_metrics()

    return {
        "metrics": metrics,
        "explanation": {
            "average_wait_pwd": "Average wait time for patients with disabilities",
            "average_wait_non_pwd": "Average wait time for patients without disabilities",
            "wait_difference": "Difference in wait times (should be < 10 minutes for equity)",
            "fairness_assessment": "Equitable if difference is small, showing PWDs get accommodation without excessive priority"
        }
    }

@app.get("/health")
def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "triage_model": "loaded",
            "queue_system": "active",
            "voice_processing": "ready"
        }
    }

# ============= BACKGROUND TASKS =============

def send_reminder_notifications():
    """Background task to send appointment reminders."""
    # Would run via Celery beat schedule
    pass

def process_voice_recordings():
    """Background task to transcribe voice recordings."""
    # Would use Whisper API
    pass

# ============= MAIN =============

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  Quadriplegic Telemedicine Platform - Starting                 ║
    ║  Accessibility: Voice-first | Eye-tracking | Switch-access     ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
