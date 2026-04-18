"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

TEACHER_ROLES = {"organizer", "admin"}
VALID_ROLES = {"student", "organizer", "admin"}


def load_teacher_accounts() -> dict:
    teacher_file = current_dir / "teachers.json"

    if not teacher_file.exists():
        return {}

    with teacher_file.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    teacher_accounts = {}

    for teacher in payload.get("teachers", []):
        username = teacher["username"]
        teacher_accounts[username] = {
            "password": teacher["password"],
            "display_name": teacher.get("display_name", username),
            "role": teacher.get("role", "organizer"),
        }

    return teacher_accounts


teacher_accounts = load_teacher_accounts()
active_sessions = {}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "requires_approval": False,
        "registrations": [
            {"email": "michael@mergington.edu", "status": "approved"},
            {"email": "daniel@mergington.edu", "status": "approved"},
        ],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "requires_approval": False,
        "registrations": [
            {"email": "emma@mergington.edu", "status": "approved"},
            {"email": "sophia@mergington.edu", "status": "approved"},
        ],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "requires_approval": False,
        "registrations": [
            {"email": "john@mergington.edu", "status": "approved"},
            {"email": "olivia@mergington.edu", "status": "approved"},
        ],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "requires_approval": True,
        "registrations": [
            {"email": "liam@mergington.edu", "status": "approved"},
            {"email": "noah@mergington.edu", "status": "approved"},
            {"email": "ella@mergington.edu", "status": "pending"},
        ],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "requires_approval": True,
        "registrations": [
            {"email": "ava@mergington.edu", "status": "approved"},
            {"email": "mia@mergington.edu", "status": "approved"},
        ],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "requires_approval": False,
        "registrations": [
            {"email": "amelia@mergington.edu", "status": "approved"},
            {"email": "harper@mergington.edu", "status": "approved"},
        ],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "requires_approval": False,
        "registrations": [
            {"email": "scarlett@mergington.edu", "status": "approved"},
            {"email": "ava@mergington.edu", "status": "rejected"},
        ],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "requires_approval": False,
        "registrations": [
            {"email": "james@mergington.edu", "status": "approved"},
            {"email": "benjamin@mergington.edu", "status": "approved"},
        ],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "requires_approval": True,
        "registrations": [
            {"email": "charlotte@mergington.edu", "status": "approved"},
            {"email": "henry@mergington.edu", "status": "approved"},
        ],
    },
}


def normalize_role(role: str) -> str:
    if role in VALID_ROLES:
        return role

    return "student"


def is_management_role(role: str) -> bool:
    return normalize_role(role) in TEACHER_ROLES


def get_session_role(session_id: Optional[str]) -> str:
    if not session_id:
        return "student"

    session = active_sessions.get(session_id)
    if not session:
        return "student"

    return normalize_role(session["role"])


def get_activity(activity_name: str) -> dict:
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    return activities[activity_name]


def get_registration(activity: dict, email: str):
    for registration in activity["registrations"]:
        if registration["email"] == email:
            return registration

    return None


def approved_registrations(activity: dict):
    return [registration for registration in activity["registrations"] if registration["status"] == "approved"]


def serialize_activity(activity_name: str, activity: dict) -> dict:
    registrations = [registration.copy() for registration in activity["registrations"]]
    approved = [registration["email"] for registration in registrations if registration["status"] == "approved"]
    pending = [registration["email"] for registration in registrations if registration["status"] == "pending"]
    rejected = [registration["email"] for registration in registrations if registration["status"] == "rejected"]

    return {
        "name": activity_name,
        "description": activity["description"],
        "schedule": activity["schedule"],
        "max_participants": activity["max_participants"],
        "requires_approval": activity["requires_approval"],
        "spots_left": activity["max_participants"] - len(approved),
        "participants": registrations,
        "approved_participants": approved,
        "pending_requests": pending,
        "rejected_requests": rejected,
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return {
        activity_name: serialize_activity(activity_name, activity)
        for activity_name, activity in activities.items()
    }


@app.post("/auth/login")
def login(username: str, password: str, response: Response):
    teacher = teacher_accounts.get(username)

    if not teacher or teacher["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_id = str(uuid4())
    active_sessions[session_id] = {
        "username": username,
        "display_name": teacher["display_name"],
        "role": normalize_role(teacher["role"]),
    }

    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")

    return {
        "username": username,
        "display_name": teacher["display_name"],
        "role": normalize_role(teacher["role"]),
    }


@app.post("/auth/logout")
def logout(session_id: Optional[str] = Cookie(default=None)):
    if session_id in active_sessions:
        del active_sessions[session_id]

    response = JSONResponse({"message": "Logged out successfully."})
    response.delete_cookie("session_id")
    return response


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    role: str = "student",
    session_id: Optional[str] = Cookie(default=None),
):
    """Request access or register a student for an activity"""
    activity = get_activity(activity_name)
    role = get_session_role(session_id)
    registration = get_registration(activity, email)

    if registration and registration["status"] == "approved":
        raise HTTPException(status_code=400, detail="Student is already registered")

    if registration and registration["status"] == "pending":
        if is_management_role(role):
            if len(approved_registrations(activity)) >= activity["max_participants"]:
                raise HTTPException(status_code=400, detail="Activity is full")

            registration["status"] = "approved"
            return {"message": f"Approved {email} for {activity_name}"}

        return {"message": f"Request already pending for {email}"}

    if activity["requires_approval"] and not is_management_role(role):
        activity["registrations"].append({"email": email, "status": "pending"})
        return {"message": f"Request submitted for {email}. It is now pending approval."}

    if len(approved_registrations(activity)) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    activity["registrations"].append({"email": email, "status": "approved"})
    return {"message": f"Registered {email} for {activity_name}"}


@app.post("/activities/{activity_name}/requests/{email}/approve")
def approve_registration(activity_name: str, email: str, session_id: Optional[str] = Cookie(default=None)):
    if not is_management_role(get_session_role(session_id)):
        raise HTTPException(status_code=403, detail="Only teachers can approve requests")

    activity = get_activity(activity_name)
    registration = get_registration(activity, email)

    if not registration:
        raise HTTPException(status_code=404, detail="Request not found")

    if registration["status"] == "approved":
        return {"message": f"{email} is already approved for {activity_name}"}

    if len(approved_registrations(activity)) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    registration["status"] = "approved"
    return {"message": f"Approved {email} for {activity_name}"}


@app.post("/activities/{activity_name}/requests/{email}/reject")
def reject_registration(activity_name: str, email: str, session_id: Optional[str] = Cookie(default=None)):
    if not is_management_role(get_session_role(session_id)):
        raise HTTPException(status_code=403, detail="Only teachers can reject requests")

    activity = get_activity(activity_name)
    registration = get_registration(activity, email)

    if not registration:
        raise HTTPException(status_code=404, detail="Request not found")

    registration["status"] = "rejected"
    return {"message": f"Rejected {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    session_id: Optional[str] = Cookie(default=None),
):
    """Unregister a student from an activity"""
    if not is_management_role(get_session_role(session_id)):
        raise HTTPException(status_code=403, detail="Only teachers can unregister students")

    activity = get_activity(activity_name)
    registration = get_registration(activity, email)

    if not registration:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activity["registrations"].remove(registration)
    return {"message": f"Unregistered {email} from {activity_name}"}
