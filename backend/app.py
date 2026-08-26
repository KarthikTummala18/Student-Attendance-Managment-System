from datetime import datetime, date, timedelta
from pathlib import Path
import csv
import io
import math
import secrets
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import hashlib
import hmac
import base64
import os

from pathlib import Path
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DB_URL = f"sqlite:///{BASE_DIR / 'edutrack.db'}"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
def hash_password(password: str) -> str:
    """Hash passwords without bcrypt/passlib compatibility issues on Python 3.13."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    student_id = Column(String)
    employee_id = Column(String)
    department = Column(String)
    semester = Column(Integer)
    section = Column(String)
    active = Column(Boolean, default=True)
    cgpa = Column(Float, default=0)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String)
    faculty_id = Column(Integer, ForeignKey("users.id"))
    department = Column(String)
    semester = Column(Integer)
    credits = Column(Integer, default=3)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    attendance_date = Column(Date)
    status = Column(String, default="present")
    session_id = Column(String)
    marked_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    from_date = Column(Date)
    to_date = Column(Date)
    reason = Column(String)
    description = Column(Text)
    document_name = Column(String)
    status = Column(String, default="pending")
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    reviewer_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String)
    description = Column(Text)
    due_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    assignment_score = Column(Float, default=0)
    midterm = Column(Float, default=0)
    final = Column(Float, default=0)
    letter = Column(String, default="B+")

class Timetable(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    day = Column(String)
    start_time = Column(String)
    end_time = Column(String)
    room = Column(String)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    message = Column(Text)
    audience = Column(String, default="all")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    code = Column(String, unique=True)

class Section(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True)
    department = Column(String)
    semester = Column(Integer)
    name = Column(String)
    capacity = Column(Integer, default=50)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer)
    action = Column(String)
    entity = Column(String)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

TOKENS = {}

def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()

def seed():
    s = SessionLocal()
    if s.query(User).count():
        s.close()
        return
    users = [
        User(name="Karthik Tummala", email="student@edutrack.local", password_hash=hash_password("student123"), role="student", student_id="CS2025XXX", department="Computer Science", semester=3, section="A", cgpa=3.82),
        User(name="Dr. Sarah Smith", email="faculty@edutrack.local", password_hash=hash_password("faculty123"), role="faculty", employee_id="FAC001", department="Computer Science"),
        User(name="Admin User", email="admin@edutrack.local", password_hash=hash_password("admin123"), role="admin", employee_id="ADM001"),
    ]
    s.add_all(users); s.flush()
    s.add_all([
        Department(name="Computer Science", code="CS"),
        Department(name="Data Science", code="DS"),
        Department(name="Information Systems", code="IS"),
        Department(name="Engineering", code="ENG"),
    ])
    s.add_all([
        Section(department="Computer Science", semester=3, name="A", capacity=50),
        Section(department="Computer Science", semester=3, name="B", capacity=50),
    ])
    courses = [
        Course(code="CS501", name="Machine Learning", faculty_id=users[1].id, department="Computer Science", semester=3, credits=3),
        Course(code="CS502", name="Database Systems", faculty_id=users[1].id, department="Computer Science", semester=3, credits=3),
        Course(code="CS503", name="Cloud Computing", faculty_id=users[1].id, department="Computer Science", semester=3, credits=3),
        Course(code="CS504", name="Data Mining", faculty_id=users[1].id, department="Computer Science", semester=3, credits=3),
    ]
    s.add_all(courses); s.flush()
    for c in courses:
        s.add(Enrollment(student_id=users[0].id, course_id=c.id))
    today = date.today()
    statuses = {
        courses[0].id: ["present"]*22 + ["absent"]*2,
        courses[1].id: ["present"]*18 + ["absent"]*6,
        courses[2].id: ["present"]*20 + ["absent"]*4,
        courses[3].id: ["present"]*15 + ["absent"]*9,
    }
    for cid, vals in statuses.items():
        for i, st in enumerate(vals):
            s.add(Attendance(student_id=users[0].id, course_id=cid, attendance_date=today-timedelta(days=i), status=st, marked_by=users[1].id))
    s.add_all([
        Grade(student_id=users[0].id, course_id=courses[0].id, assignment_score=92, midterm=88, final=91, letter="A"),
        Grade(student_id=users[0].id, course_id=courses[1].id, assignment_score=89, midterm=84, final=87, letter="A-"),
        Grade(student_id=users[0].id, course_id=courses[2].id, assignment_score=86, midterm=82, final=84, letter="B+"),
        Grade(student_id=users[0].id, course_id=courses[3].id, assignment_score=93, midterm=90, final=94, letter="A"),
    ])
    s.add_all([
        Timetable(course_id=courses[0].id, day="Monday", start_time="09:00", end_time="10:00", room="SCI-201"),
        Timetable(course_id=courses[1].id, day="Monday", start_time="11:00", end_time="12:00", room="SCI-202"),
        Timetable(course_id=courses[2].id, day="Monday", start_time="14:00", end_time="15:00", room="SCI-203"),
        Timetable(course_id=courses[3].id, day="Tuesday", start_time="16:00", end_time="17:00", room="SCI-204"),
    ])
    s.add_all([
        Assignment(course_id=courses[0].id, title="ML Assignment 3", description="Build a classification model and report evaluation metrics.", due_date=today+timedelta(days=4)),
        Assignment(course_id=courses[1].id, title="SQL Optimization", description="Optimize five slow SQL queries.", due_date=today+timedelta(days=7)),
    ])
    s.add_all([
        Announcement(title="Database Systems", message="Tomorrow's class will be moved to Room SCI-202.", audience="all", created_by=users[1].id),
        Announcement(title="Semester 3 Examination Notice", message="Exam schedule will be published this week.", audience="all", created_by=users[2].id),
    ])
    for u in users:
        s.add(Notification(user_id=u.id, title="Welcome to EduTrack", message="Your account is ready. Explore your dashboard."))
    settings = [
        ("minimum_attendance","75"), ("warning_threshold","80"), ("critical_threshold","65"),
        ("late_after_minutes","10"), ("qr_session_minutes","5")
    ]
    s.add_all([Setting(key=k,value=v) for k,v in settings])
    s.commit(); s.close()

seed()

app = FastAPI(title="EduTrack API", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")



BASE_DIR = Path(__file__).resolve().parent.parent

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "frontend" / "index.html")

class LoginIn(BaseModel):
    email: str
    password: str

class LeaveIn(BaseModel):
    from_date: date
    to_date: date
    reason: str
    description: str = ""
    document_name: str = ""

class AttendanceIn(BaseModel):
    course_id: int
    attendance_date: date
    student_id: int
    status: str

class AssignmentIn(BaseModel):
    course_id: int
    title: str
    description: str
    due_date: date

class GradeIn(BaseModel):
    student_id: int
    course_id: int
    assignment_score: float = 0
    midterm: float = 0
    final: float = 0
    letter: str = "B+"

class AnnouncementIn(BaseModel):
    title: str
    message: str
    audience: str = "all"

class UserIn(BaseModel):
    name: str
    email: str
    password: str = "Welcome123!"
    role: str
    department: str = ""
    semester: Optional[int] = None
    section: str = ""

class SettingsIn(BaseModel):
    minimum_attendance: int
    warning_threshold: int
    critical_threshold: int
    late_after_minutes: int
    qr_session_minutes: int

def current_user(request: Request, s: Session = Depends(db)):
    token = request.headers.get("Authorization","").replace("Bearer ","")
    uid = TOKENS.get(token)
    if not uid:
        raise HTTPException(401, "Not authenticated")
    u = s.get(User, uid)
    if not u or not u.active:
        raise HTTPException(401, "Account inactive")
    return u

def require_roles(*roles):
    def dep(u=Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return u
    return dep

def audit(s, actor, action, entity, details=""):
    s.add(AuditLog(actor_id=actor.id, action=action, entity=entity, details=details))

def course_name(s, cid):
    c=s.get(Course,cid)
    return c.name if c else "Unknown"

def attendance_stats(s, student_id):
    rows=s.query(Attendance).filter(Attendance.student_id==student_id).all()
    total=len(rows); present=sum(r.status in ("present","late","excused") for r in rows)
    pct=round(present/total*100,1) if total else 0
    return total,present,pct

@app.post("/api/login")
def login(data: LoginIn, s: Session=Depends(db)):
    u=s.query(User).filter(User.email==data.email).first()
    if not u or not verify_password(data.password,u.password_hash):
        raise HTTPException(401,"Invalid email or password")
    token=secrets.token_urlsafe(32); TOKENS[token]=u.id
    audit(s,u,"LOGIN","AUTH","Successful login")
    s.commit()
    return {"token":token,"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role,"student_id":u.student_id,"department":u.department,"semester":u.semester,"section":u.section,"cgpa":u.cgpa}}

@app.post("/api/logout")
def logout(request: Request):
    token=request.headers.get("Authorization","").replace("Bearer ","")
    TOKENS.pop(token,None)
    return {"ok":True}

@app.get("/api/me")
def me(u=Depends(current_user)):
    return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"student_id":u.student_id,"employee_id":u.employee_id,"department":u.department,"semester":u.semester,"section":u.section,"cgpa":u.cgpa}

@app.get("/api/dashboard")
def dashboard(u=Depends(current_user), s: Session=Depends(db)):
    if u.role=="student":
        total,present,pct=attendance_stats(s,u.id)
        enroll=s.query(Enrollment).filter_by(student_id=u.id).all()
        courses=[]
        for e in enroll:
            c=s.get(Course,e.course_id)
            rows=s.query(Attendance).filter_by(student_id=u.id,course_id=c.id).all()
            p=sum(x.status in ("present","late","excused") for x in rows)
            courses.append({"id":c.id,"code":c.code,"name":c.name,"credits":c.credits,"attendance":round(p/len(rows)*100,1) if rows else 0})
        return {"attendance":pct,"total_classes":total,"present_classes":present,"cgpa":u.cgpa,"courses":courses}
    if u.role=="faculty":
        courses=s.query(Course).filter_by(faculty_id=u.id).all()
        student_ids={e.student_id for c in courses for e in s.query(Enrollment).filter_by(course_id=c.id).all()}
        rows=s.query(Attendance).filter(Attendance.course_id.in_([c.id for c in courses])).all() if courses else []
        pct=round(sum(r.status in ("present","late","excused") for r in rows)/len(rows)*100,1) if rows else 0
        pending=s.query(LeaveRequest).filter_by(status="pending").count()
        return {"courses":[{"id":c.id,"code":c.code,"name":c.name,"students":s.query(Enrollment).filter_by(course_id=c.id).count()} for c in courses],"student_count":len(student_ids),"attendance":pct,"pending_leaves":pending}
    return {
        "students":s.query(User).filter_by(role="student",active=True).count(),
        "faculty":s.query(User).filter_by(role="faculty",active=True).count(),
        "courses":s.query(Course).count(),
        "departments":s.query(Department).count(),
        "pending_leaves":s.query(LeaveRequest).filter_by(status="pending").count(),
        "at_risk": sum(1 for st in s.query(User).filter_by(role="student",active=True).all() if attendance_stats(s,st.id)[2] < 75)
    }

@app.get("/api/attendance")
def get_attendance(u=Depends(current_user), s: Session=Depends(db)):
    target_id=u.id
    if u.role=="student":
        rows=s.query(Attendance).filter_by(student_id=target_id).order_by(Attendance.attendance_date.desc()).all()
    else:
        course_ids=[c.id for c in s.query(Course).filter_by(faculty_id=u.id).all()] if u.role=="faculty" else [c.id for c in s.query(Course).all()]
        rows=s.query(Attendance).filter(Attendance.course_id.in_(course_ids)).order_by(Attendance.attendance_date.desc()).limit(300).all() if course_ids else []
    return [{"id":r.id,"student_id":r.student_id,"course_id":r.course_id,"course":course_name(s,r.course_id),"date":r.attendance_date.isoformat(),"status":r.status} for r in rows]

@app.get("/api/attendance/summary")
def attendance_summary(u=Depends(current_user), s: Session=Depends(db)):
    student_ids=[u.id] if u.role=="student" else [x.id for x in s.query(User).filter_by(role="student",active=True).all()]
    out=[]
    for sid in student_ids:
        st=s.get(User,sid); total,present,pct=attendance_stats(s,sid)
        by={}
        for r in s.query(Attendance).filter_by(student_id=sid).all():
            by.setdefault(r.course_id,[]).append(r)
        subjects=[]
        for cid,rs in by.items():
            pp=sum(x.status in ("present","late","excused") for x in rs)
            subjects.append({"course":course_name(s,cid),"course_id":cid,"present":pp,"total":len(rs),"attendance":round(pp/len(rs)*100,1)})
        out.append({"student_id":sid,"name":st.name,"overall":pct,"total":total,"present":present,"subjects":subjects})
    return out

@app.post("/api/attendance")
def mark_attendance(data: AttendanceIn, u=Depends(require_roles("faculty","admin")), s: Session=Depends(db)):
    row=Attendance(student_id=data.student_id,course_id=data.course_id,attendance_date=data.attendance_date,status=data.status,marked_by=u.id)
    s.add(row); audit(s,u,"MARK_ATTENDANCE","Attendance",f"student={data.student_id},course={data.course_id},status={data.status}"); s.commit()
    return {"ok":True,"id":row.id}

@app.post("/api/attendance/qr")
def create_qr(course_id:int, u=Depends(require_roles("faculty","admin")), s:Session=Depends(db)):
    session=secrets.token_urlsafe(10)
    audit(s,u,"CREATE_QR","AttendanceSession",f"course={course_id},session={session}"); s.commit()
    return {"session_id":session,"course_id":course_id,"expires_in_minutes":int(s.query(Setting).filter_by(key="qr_session_minutes").first().value)}

@app.get("/api/courses")
def courses(u=Depends(current_user),s:Session=Depends(db)):
    if u.role=="student":
        cs=[s.get(Course,e.course_id) for e in s.query(Enrollment).filter_by(student_id=u.id).all()]
    elif u.role=="faculty":
        cs=s.query(Course).filter_by(faculty_id=u.id).all()
    else: cs=s.query(Course).all()
    return [{"id":c.id,"code":c.code,"name":c.name,"department":c.department,"semester":c.semester,"credits":c.credits,"faculty_id":c.faculty_id} for c in cs]

@app.get("/api/leaves")
def leaves(u=Depends(current_user),s:Session=Depends(db)):
    q=s.query(LeaveRequest)
    if u.role=="student": q=q.filter_by(student_id=u.id)
    elif u.role=="faculty": q=q.filter(LeaveRequest.reviewer_id==u.id)
    rows=q.order_by(LeaveRequest.created_at.desc()).all()
    return [{"id":r.id,"student_id":r.student_id,"student":s.get(User,r.student_id).name,"from_date":r.from_date.isoformat(),"to_date":r.to_date.isoformat(),"reason":r.reason,"description":r.description,"document":r.document_name,"status":r.status,"comment":r.reviewer_comment or ""} for r in rows]

@app.post("/api/leaves")
def create_leave(data:LeaveIn,u=Depends(require_roles("student")),s:Session=Depends(db)):
    reviewer=s.query(User).filter_by(role="faculty",department=u.department,active=True).first()
    r=LeaveRequest(student_id=u.id,from_date=data.from_date,to_date=data.to_date,reason=data.reason,description=data.description,document_name=data.document_name,reviewer_id=reviewer.id if reviewer else None)
    s.add(r); s.flush()
    if reviewer: s.add(Notification(user_id=reviewer.id,title="New leave request",message=f"{u.name} submitted a leave request."))
    audit(s,u,"CREATE_LEAVE","LeaveRequest",f"id={r.id}"); s.commit()
    return {"id":r.id,"status":r.status}

@app.post("/api/leaves/{leave_id}/{action}")
def review_leave(leave_id:int,action:str,u=Depends(require_roles("faculty","admin")),s:Session=Depends(db)):
    if action not in ("approve","reject","cancel"): raise HTTPException(400,"Invalid action")
    r=s.get(LeaveRequest,leave_id)
    if not r: raise HTTPException(404,"Leave not found")
    r.status={"approve":"approved","reject":"rejected","cancel":"cancelled"}[action]
    r.reviewer_id=u.id
    s.add(Notification(user_id=r.student_id,title=f"Leave {r.status}",message=f"Leave request #{r.id} is {r.status}."))
    audit(s,u,"REVIEW_LEAVE","LeaveRequest",f"id={r.id},status={r.status}"); s.commit()
    return {"ok":True,"status":r.status}

@app.get("/api/assignments")
def assignments(u=Depends(current_user),s:Session=Depends(db)):
    if u.role=="student":
        cids=[e.course_id for e in s.query(Enrollment).filter_by(student_id=u.id).all()]
    elif u.role=="faculty": cids=[c.id for c in s.query(Course).filter_by(faculty_id=u.id).all()]
    else: cids=[c.id for c in s.query(Course).all()]
    rows=s.query(Assignment).filter(Assignment.course_id.in_(cids)).order_by(Assignment.due_date).all() if cids else []
    return [{"id":r.id,"course_id":r.course_id,"course":course_name(s,r.course_id),"title":r.title,"description":r.description,"due_date":r.due_date.isoformat()} for r in rows]

@app.post("/api/assignments")
def create_assignment(data:AssignmentIn,u=Depends(require_roles("faculty","admin")),s:Session=Depends(db)):
    r=Assignment(**data.model_dump()); s.add(r); audit(s,u,"CREATE_ASSIGNMENT","Assignment",data.title); s.commit(); return {"id":r.id}

@app.get("/api/grades")
def grades(u=Depends(current_user),s:Session=Depends(db)):
    q=s.query(Grade)
    if u.role=="student": q=q.filter_by(student_id=u.id)
    elif u.role=="faculty":
        ids=[c.id for c in s.query(Course).filter_by(faculty_id=u.id).all()]; q=q.filter(Grade.course_id.in_(ids))
    rows=q.all()
    return [{"id":g.id,"student_id":g.student_id,"student":s.get(User,g.student_id).name,"course_id":g.course_id,"course":course_name(s,g.course_id),"assignment_score":g.assignment_score,"midterm":g.midterm,"final":g.final,"letter":g.letter} for g in rows]

@app.post("/api/grades")
def create_grade(data:GradeIn,u=Depends(require_roles("faculty","admin")),s:Session=Depends(db)):
    g=Grade(**data.model_dump()); s.add(g); audit(s,u,"SAVE_GRADE","Grade",f"student={data.student_id},course={data.course_id}"); s.commit(); return {"id":g.id}

@app.get("/api/timetable")
def timetable(u=Depends(current_user),s:Session=Depends(db)):
    if u.role=="student": cids=[e.course_id for e in s.query(Enrollment).filter_by(student_id=u.id).all()]
    elif u.role=="faculty": cids=[c.id for c in s.query(Course).filter_by(faculty_id=u.id).all()]
    else: cids=[c.id for c in s.query(Course).all()]
    rows=s.query(Timetable).filter(Timetable.course_id.in_(cids)).all() if cids else []
    return [{"id":r.id,"course":course_name(s,r.course_id),"course_id":r.course_id,"day":r.day,"start":r.start_time,"end":r.end_time,"room":r.room} for r in rows]

@app.get("/api/announcements")
def announcements(u=Depends(current_user),s:Session=Depends(db)):
    rows=s.query(Announcement).order_by(Announcement.created_at.desc()).limit(50).all()
    return [{"id":r.id,"title":r.title,"message":r.message,"audience":r.audience,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/announcements")
def create_announcement(data:AnnouncementIn,u=Depends(require_roles("faculty","admin")),s:Session=Depends(db)):
    r=Announcement(**data.model_dump(),created_by=u.id); s.add(r)
    users=s.query(User).filter(User.active==True).all()
    for x in users:
        s.add(Notification(user_id=x.id,title=data.title,message=data.message))
    audit(s,u,"CREATE_ANNOUNCEMENT","Announcement",data.title); s.commit(); return {"id":r.id}

@app.get("/api/notifications")
def notifications(u=Depends(current_user),s:Session=Depends(db)):
    rows=s.query(Notification).filter_by(user_id=u.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [{"id":r.id,"title":r.title,"message":r.message,"read":r.read,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/notifications/{nid}/read")
def mark_notification(nid:int,u=Depends(current_user),s:Session=Depends(db)):
    r=s.query(Notification).filter_by(id=nid,user_id=u.id).first()
    if r: r.read=True; s.commit()
    return {"ok":True}

@app.get("/api/users")
def users(u=Depends(require_roles("admin")),s:Session=Depends(db)):
    return [{"id":x.id,"name":x.name,"email":x.email,"role":x.role,"department":x.department,"semester":x.semester,"section":x.section,"active":x.active} for x in s.query(User).order_by(User.name).all()]

@app.post("/api/users")
def create_user(data:UserIn,u=Depends(require_roles("admin")),s:Session=Depends(db)):
    if s.query(User).filter_by(email=data.email).first(): raise HTTPException(400,"Email already exists")
    x=User(name=data.name,email=data.email,password_hash=hash_password(data.password),role=data.role,department=data.department,semester=data.semester,section=data.section,active=True)
    s.add(x); audit(s,u,"CREATE_USER","User",data.email); s.commit(); return {"id":x.id}

@app.post("/api/users/{uid}/toggle")
def toggle_user(uid:int,u=Depends(require_roles("admin")),s:Session=Depends(db)):
    x=s.get(User,uid)
    if not x: raise HTTPException(404,"User not found")
    x.active=not x.active; audit(s,u,"TOGGLE_USER","User",f"id={uid},active={x.active}"); s.commit(); return {"active":x.active}

@app.get("/api/departments")
def departments(u=Depends(current_user),s:Session=Depends(db)):
    return [{"id":x.id,"name":x.name,"code":x.code} for x in s.query(Department).all()]

@app.get("/api/sections")
def sections(u=Depends(current_user),s:Session=Depends(db)):
    return [{"id":x.id,"department":x.department,"semester":x.semester,"name":x.name,"capacity":x.capacity} for x in s.query(Section).all()]

@app.get("/api/settings")
def settings(u=Depends(require_roles("admin")),s:Session=Depends(db)):
    return {x.key:x.value for x in s.query(Setting).all()}

@app.put("/api/settings")
def update_settings(data:SettingsIn,u=Depends(require_roles("admin")),s:Session=Depends(db)):
    mapping={"minimum_attendance":data.minimum_attendance,"warning_threshold":data.warning_threshold,"critical_threshold":data.critical_threshold,"late_after_minutes":data.late_after_minutes,"qr_session_minutes":data.qr_session_minutes}
    for k,v in mapping.items():
        r=s.query(Setting).filter_by(key=k).first()
        if r:r.value=str(v)
    audit(s,u,"UPDATE_SETTINGS","Settings","Attendance and QR settings updated"); s.commit(); return {"ok":True}

@app.get("/api/audit")
def audit_logs(u=Depends(require_roles("admin")),s:Session=Depends(db)):
    rows=s.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return [{"id":r.id,"actor":s.get(User,r.actor_id).name if s.get(User,r.actor_id) else "System","action":r.action,"entity":r.entity,"details":r.details,"created_at":r.created_at.isoformat()} for r in rows]

@app.get("/api/report/attendance.csv")
def attendance_csv(u=Depends(current_user),s:Session=Depends(db)):
    rows=attendance_summary(u,s)
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Student","Student ID","Overall Attendance","Present","Total"])
    for r in rows:w.writerow([r["name"],r["student_id"],r["overall"],r["present"],r["total"]])
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=attendance_report.csv"})

@app.get("/api/ai")
def ai(q:str,u=Depends(current_user),s:Session=Depends(db)):
    text=q.lower()
    if u.role=="student":
        total,present,pct=attendance_stats(s,u.id)
        if "attendance" in text:
            return {"answer":f"Your current attendance is {pct}%. You have attended {present} of {total} recorded classes."}
        if "miss" in text:
            target=75/100
            # x misses possible while current attendance remains >= target
            m=0
            while total and (present/(total+m+1))*100 >= 75: m+=1
            return {"answer":f"You can miss approximately {m} more recorded classes and remain at or above 75%, based on your current data."}
        return {"answer":"I can help with attendance, leave status, courses, grades, timetable, and upcoming assignments."}
    if u.role=="faculty":
        at=[]
        for st in s.query(User).filter_by(role="student",active=True).all():
            pct=attendance_stats(s,st.id)[2]
            if pct<75:at.append((st.name,pct))
        if "risk" in text or "at risk" in text:
            return {"answer":f"There are {len(at)} students below 75% attendance. " + ", ".join(f"{n} ({p}%)" for n,p in at[:6])}
        return {"answer":"I can summarize your class attendance, identify at-risk students, and explain leave/assignment status."}
    if "lowest" in text or "department" in text:
        vals=[]
        for d in s.query(Department).all():
            students=s.query(User).filter_by(role="student",department=d.name,active=True).all()
            pcts=[attendance_stats(s,x.id)[2] for x in students]
            vals.append((d.name,round(sum(pcts)/len(pcts),1) if pcts else 0))
        vals.sort(key=lambda x:x[1])
        return {"answer":f"{vals[0][0]} has the lowest average attendance at {vals[0][1]}%." if vals else "No attendance data is available."}
    return {"answer":"I can summarize institution-wide attendance, at-risk students, leave requests, courses, and reports."}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("backend.app:app",host="127.0.0.1",port=8000,reload=True)
