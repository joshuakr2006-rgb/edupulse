import os, datetime, statistics
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')
from sqlalchemy import text, inspect
import uuid, mimetypes, joblib
import jwt

app = Flask(__name__)
CORS(app, origins=os.getenv('CLIENT_ORIGIN', '*').split(','))
uri = os.getenv('DATABASE_URL', 'sqlite:///education.db')
if uri.startswith('postgres://'): uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'change-this-before-deploying')
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(Path(__file__).parent / 'uploads')))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILES = int(os.getenv('MAX_FILES_PER_SUBMISSION', '5'))
MAX_FILE_BYTES = int(os.getenv('MAX_FILE_SIZE_MB', '20')) * 1024 * 1024
MAX_TOTAL_BYTES = int(os.getenv('MAX_TOTAL_UPLOAD_MB', '50')) * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf','doc','docx','jpg','jpeg','png','txt','rtf','odt','xls','xlsx','csv','ppt','pptx','zip'}
app.config['MAX_CONTENT_LENGTH'] = MAX_TOTAL_BYTES + 1024 * 1024
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    student_code = db.Column(db.String(30), unique=True)
    section = db.Column(db.String(30), default='CSE General - E')

class Metric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_code = db.Column(db.String(30), nullable=False)
    course_name = db.Column(db.String(120), nullable=False)
    attendance = db.Column(db.Float, default=80)
    assignment_avg = db.Column(db.Float, default=75)
    assessment_avg = db.Column(db.Float, default=70)
    engagement = db.Column(db.Float, default=75)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    student = db.relationship('User', backref='metrics')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(40), default='Assessment')
    status = db.Column(db.String(30), default='Open')
    due_label = db.Column(db.String(80), default='This week')
    course_code = db.Column(db.String(30), default='CSE')

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='New')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    student = db.relationship('User')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    teacher = db.relationship('User')
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id','course_id'),)
    student = db.relationship('User')
    course = db.relationship('Course')

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    class_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(12), nullable=False, default='present')
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course')

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default='')
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    max_score = db.Column(db.Float, nullable=False, default=100)
    course = db.relationship('Course')
    teacher = db.relationship('User')

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    score = db.Column(db.Float)
    feedback = db.Column(db.Text, default='')
    assignment = db.relationship('Assignment')
    student = db.relationship('User')
    __table_args__ = (db.UniqueConstraint('assignment_id','student_id'),)

class SubmissionFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), unique=True, nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    submission = db.relationship('Submission', backref=db.backref('files', cascade='all, delete-orphan'))

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Trained Random Forest classifier. The bundled pilot artifact is trained on synthetic
# educational patterns; institutional deployment must recalibrate it on validated local outcomes.
MODEL_PATH = Path(__file__).parent / 'student_risk_model.joblib'
RISK_MODEL = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

def predict(m):
    features = [[float(m.attendance), float(m.assignment_avg), float(m.assessment_avg), float(m.engagement)]]
    if RISK_MODEL is not None:
        probabilities = RISK_MODEL.predict_proba(features)[0]
        classes = list(RISK_MODEL.classes_)
        level = str(classes[int(probabilities.argmax())])
        risk = round(float(probabilities[classes.index('High')] + 0.5 * probabilities[classes.index('Moderate')]) * 100, 1)
    else:
        risk = round(min(100, max(0, (75-m.attendance)*0.45 + (65-m.assignment_avg)*0.22 +
                                 (60-m.assessment_avg)*0.25 + (60-m.engagement)*0.08)), 1)
        level = 'High' if risk >= 24 or m.attendance < 60 or m.assessment_avg < 40 else ('Moderate' if risk >= 10 or m.attendance < 75 else 'Low')
    reasons = []
    if m.attendance < 75: reasons.append(f'Attendance is {m.attendance:.0f}%, below the 75% target')
    if m.assignment_avg < 65: reasons.append(f'Assignment average is {m.assignment_avg:.0f}%')
    if m.assessment_avg < 60: reasons.append(f'Assessment average is {m.assessment_avg:.0f}%')
    if m.engagement < 60: reasons.append('Learning engagement has declined')
    if not reasons: reasons.append('No major warning signal; continue regular monitoring')
    rec = 'Schedule a one-to-one check-in, agree on a short recovery plan, and review progress next week.' if level == 'High' else ('Share targeted practice material and check progress in the next class.' if level == 'Moderate' else 'Maintain current study habits and review progress at the next assessment.')
    return {'risk_score': risk, 'risk_level': level, 'reasons': reasons, 'recommendation': rec}

def token_for(user):
    return jwt.encode({'sub': str(user.id), 'role': user.role, 'exp': datetime.datetime.utcnow()+datetime.timedelta(hours=12)}, app.config['SECRET_KEY'], algorithm='HS256')

def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        raw = request.headers.get('Authorization', '')
        try:
            payload = jwt.decode(raw.replace('Bearer ', ''), app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user = db.session.get(User, int(payload['sub']))
            if not g.user: raise ValueError('User not found')
        except Exception:
            return jsonify({'error':'Please log in again.'}), 401
        return fn(*args, **kwargs)
    return wrapped

def metric_json(m):
    return {'id':m.id, 'student_id':m.student_id, 'student_name':m.student.name, 'student_code':m.student.student_code, 'course_code':m.course_code, 'course_name':m.course_name, 'attendance':m.attendance, 'assignment_avg':m.assignment_avg, 'assessment_avg':m.assessment_avg, 'engagement':m.engagement, **predict(m)}

def seed():
    """Create schema; never generate demo users or academic records."""
    db.create_all()
    course_columns = {column['name'] for column in inspect(db.engine).get_columns('course')}
    if 'teacher_id' not in course_columns:
        with db.engine.begin() as connection:
            connection.execute(text('ALTER TABLE course ADD COLUMN teacher_id INTEGER REFERENCES user(id)'))
    if os.getenv('PURGE_LEGACY_DEMO_DATA', 'false').lower() == 'true':
        demo_users = User.query.filter(User.email.like('%@demo.edu')).all()
        demo_ids = [u.id for u in demo_users]
        demo_assignment_ids = [a.id for a in Assignment.query.filter(Assignment.teacher_id.in_(demo_ids)).all()] if demo_ids else []
        sub_query = Submission.query.filter(
            (Submission.student_id.in_(demo_ids)) | (Submission.assignment_id.in_(demo_assignment_ids))
        ) if demo_ids else Submission.query.filter(Submission.assignment_id.in_(demo_assignment_ids))
        demo_submissions = sub_query.all()
        for submission in demo_submissions:
            for attachment in submission.files:
                (UPLOAD_DIR / attachment.stored_name).unlink(missing_ok=True)
                db.session.delete(attachment)
            db.session.delete(submission)
        if demo_assignment_ids:
            Assignment.query.filter(Assignment.id.in_(demo_assignment_ids)).delete(synchronize_session=False)
        if demo_ids:
            Course.query.filter(Course.teacher_id.in_(demo_ids)).update({'teacher_id': None}, synchronize_session=False)
            AttendanceRecord.query.filter((AttendanceRecord.student_id.in_(demo_ids)) | (AttendanceRecord.marked_by.in_(demo_ids))).delete(synchronize_session=False)
            Metric.query.filter(Metric.student_id.in_(demo_ids)).delete(synchronize_session=False)
            Alert.query.filter(Alert.student_id.in_(demo_ids)).delete(synchronize_session=False)
            Enrollment.query.filter(Enrollment.student_id.in_(demo_ids)).delete(synchronize_session=False)
            User.query.filter(User.id.in_(demo_ids)).delete(synchronize_session=False)
        # Seed-only dashboard placeholders are not part of the production dataset.
        Activity.query.delete(); Notice.query.delete()
        db.session.commit()
    email = os.getenv('INITIAL_TEACHER_EMAIL', '').strip().lower()
    password = os.getenv('INITIAL_TEACHER_PASSWORD', '')
    name = os.getenv('INITIAL_TEACHER_NAME', 'Platform Administrator').strip()
    teacher = User.query.filter_by(email=email).first() if email else None
    if email and password and not teacher:
        teacher = User(name=name, email=email, password=generate_password_hash(password),
                       role='teacher', section='Administration')
        db.session.add(teacher); db.session.flush()
    if teacher and teacher.role == 'teacher':
        # Existing unassigned catalogue rows can be claimed by the configured administrator.
        Course.query.filter_by(teacher_id=None).update({'teacher_id': teacher.id})
    db.session.commit()

@app.get('/api/health')
def health(): return jsonify({'status':'ok','service':'EduPulse API','ml_model_loaded':RISK_MODEL is not None})

@app.get('/api/model/info')
@auth_required
def model_info():
    return jsonify({'model':'RandomForestClassifier','loaded':RISK_MODEL is not None,
      'features':['attendance','assignment_avg','assessment_avg','engagement'],
      'classes':['Low','Moderate','High'],
      'training_note':'Bundled pilot model was trained on synthetic educational patterns. Validate and retrain with consented, representative institutional records before consequential use.'})

@app.post('/api/auth/login')
def login():
    data=request.get_json(silent=True) or {}
    email=(data.get('email') or '').strip().lower(); password=data.get('password') or ''; role=data.get('role')
    user=User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password,password): return jsonify({'error':'Invalid email or password.'}),401
    if role and user.role != role: return jsonify({'error':f'This account is registered as a {user.role}. Choose the correct login.'}),403
    return jsonify({'token':token_for(user),'user':{'id':user.id,'name':user.name,'email':user.email,'role':user.role,'student_code':user.student_code,'section':user.section}})

@app.get('/api/me')
@auth_required
def me(): return jsonify({'id':g.user.id,'name':g.user.name,'email':g.user.email,'role':g.user.role,'student_code':g.user.student_code,'section':g.user.section})

@app.get('/api/dashboard')
@auth_required
def dashboard():
    if g.user.role=='student':
        metrics=Metric.query.filter_by(student_id=g.user.id).all(); alerts=Alert.query.filter_by(student_id=g.user.id).order_by(Alert.created_at.desc()).all()
        attendance=round(statistics.mean([m.attendance for m in metrics]),1) if metrics else 0
        assessment=round(statistics.mean([m.assessment_avg for m in metrics]),1) if metrics else 0
        assignment=round(statistics.mean([m.assignment_avg for m in metrics]),1) if metrics else 0
        return jsonify({'stats':{'attendance':attendance,'assessment_avg':assessment,'assignment_avg':assignment,'courses':len(metrics)},'metrics':[metric_json(m) for m in metrics],'alerts':[{'id':a.id,'title':a.title,'message':a.message,'severity':a.severity,'status':a.status,'created_at':a.created_at.isoformat()} for a in alerts], 'activities':activity_data(), 'notices':notice_data()})
    metrics=Metric.query.all(); students={s.id:s for s in User.query.filter_by(role='student').all()}
    summaries=[]
    for s in students.values():
        sm=[m for m in metrics if m.student_id==s.id]; predictions=[predict(m) for m in sm]
        level='High' if any(p['risk_level']=='High' for p in predictions) else ('Moderate' if any(p['risk_level']=='Moderate' for p in predictions) else 'Low')
        summaries.append({'id':s.id,'name':s.name,'student_code':s.student_code,'attendance':round(statistics.mean([m.attendance for m in sm]),1) if sm else 0,'assessment_avg':round(statistics.mean([m.assessment_avg for m in sm]),1) if sm else 0,'assignment_avg':round(statistics.mean([m.assignment_avg for m in sm]),1) if sm else 0,'risk_level':level,'risk_score':max([p['risk_score'] for p in predictions],default=0),'course_count':len(sm)})
    alerts=Alert.query.order_by(Alert.created_at.desc()).all()
    return jsonify({'stats':{'students':len(students),'high_risk':sum(1 for s in summaries if s['risk_level']=='High'),'moderate_risk':sum(1 for s in summaries if s['risk_level']=='Moderate'),'avg_attendance':round(statistics.mean([s['attendance'] for s in summaries]),1) if summaries else 0,'open_alerts':sum(1 for a in alerts if a.status!='Resolved')},'students':summaries,'metrics':[metric_json(m) for m in metrics],'alerts':[{'id':a.id,'student_name':a.student.name,'student_code':a.student.student_code,'title':a.title,'message':a.message,'severity':a.severity,'status':a.status,'created_at':a.created_at.isoformat()} for a in alerts],'activities':activity_data(),'notices':notice_data()})

def activity_data(): return [{'id':a.id,'title':a.title,'category':a.category,'status':a.status,'due_label':a.due_label,'course_code':a.course_code} for a in Activity.query.order_by(Activity.id).all()]
def notice_data(): return [{'id':n.id,'title':n.title,'body':n.body,'created_at':n.created_at.isoformat()} for n in Notice.query.order_by(Notice.created_at.desc()).all()]

@app.get('/api/students')
@auth_required
def students():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    result=[]
    for s in User.query.filter_by(role='student').all():
        ms=Metric.query.filter_by(student_id=s.id).all(); ps=[predict(m) for m in ms]
        result.append({'id':s.id,'name':s.name,'student_code':s.student_code,'email':s.email,'metrics':[metric_json(m) for m in ms], 'risk_level':'High' if any(p['risk_level']=='High' for p in ps) else ('Moderate' if any(p['risk_level']=='Moderate' for p in ps) else 'Low')})
    return jsonify(result)

@app.patch('/api/alerts/<int:alert_id>')
@auth_required
def update_alert(alert_id):
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    alert=db.session.get(Alert,alert_id)
    if not alert: return jsonify({'error':'Alert not found'}),404
    status=(request.get_json(silent=True) or {}).get('status','Reviewed')
    if status not in ['New','Reviewed','Resolved']: return jsonify({'error':'Invalid status'}),400
    alert.status=status; db.session.commit(); return jsonify({'id':alert.id,'status':alert.status})

@app.post('/api/metrics')
@auth_required
def add_metric():
    if g.user.role != 'teacher':
        return jsonify({'error': 'Teacher access required'}), 403

    d = request.get_json(silent=True) or {}

    try:
        # Get student
        student_id = int(d['student_id'])
        student = db.session.get(User, student_id)

        # Get course using course_id or course_code
        if d.get('course_id'):
            course = db.session.get(Course, int(d['course_id']))
        else:
            code = str(d.get('course_code', '')).strip().upper()
            name = str(d.get('course_name', '')).strip()

            if not code or not name:
                raise ValueError()

            course = Course.query.filter_by(code=code).first()

            if course and course.teacher_id != g.user.id:
                raise ValueError()

            if not course:
                course = Course(
                    code=code,
                    name=name,
                    teacher_id=g.user.id
                )
                db.session.add(course)
                db.session.flush()

        # Validate student and course ownership
        if (
            not student
            or student.role != 'student'
            or not course
            or course.teacher_id != g.user.id
        ):
            raise ValueError()

        # Create enrollment if necessary
        enrollment = Enrollment.query.filter_by(
            student_id=student.id,
            course_id=course.id
        ).first()

        if not enrollment:
            db.session.add(
                Enrollment(
                    student_id=student.id,
                    course_id=course.id
                )
            )

        # Save academic metrics
        m = Metric(
            student_id=student_id,
            course_code=course.code,
            course_name=course.name,
            attendance=float(d['attendance']),
            assignment_avg=float(d['assignment_avg']),
            assessment_avg=float(d['assessment_avg']),
            engagement=float(d.get('engagement', 70))
        )

        if any(
            x < 0 or x > 100
            for x in [
                m.attendance,
                m.assignment_avg,
                m.assessment_avg,
                m.engagement
            ]
        ):
            return jsonify({'error': 'Scores must be between 0 and 100'}), 400

        db.session.add(m)
        db.session.flush()

        # Generate ML prediction
        p = predict(m)

        if p['risk_level'] == 'High':
            db.session.add(
                Alert(
                    student_id=student.id,
                    title=f'Academic early warning: {m.course_code}',
                    message=(
                        f'{student.name} may need support in '
                        f'{m.course_name}. '
                        + '; '.join(p['reasons'])
                    ),
                    severity='high'
                )
            )

        db.session.commit()

        return jsonify(metric_json(m)), 201

    except (KeyError, ValueError, TypeError):
        db.session.rollback()
        return jsonify({
            'error': 'Please provide a valid student and all required numeric scores.'
        }), 400
@app.get('/api/courses')
@auth_required
def list_courses():
    rows=Course.query.filter_by(teacher_id=g.user.id).order_by(Course.code).all() if g.user.role=='teacher' else Course.query.order_by(Course.code).all()
    if g.user.role=='student':
        ids=[e.course_id for e in Enrollment.query.filter_by(student_id=g.user.id).all()]
        rows=[c for c in rows if c.id in ids]
    return jsonify([{'id':c.id,'code':c.code,'name':c.name} for c in rows])

@app.get('/api/courses/<int:course_id>/students')
@auth_required
def course_students(course_id):
    if g.user.role != 'teacher': return jsonify({'error':'Teacher access required'}),403
    course=db.session.get(Course,course_id)
    if not course: return jsonify({'error':'Course not found'}),404
    if course.teacher_id != g.user.id: return jsonify({'error':'You are not assigned to this course.'}),403
    rows=Enrollment.query.filter_by(course_id=course_id).all()
    return jsonify([{'id':e.student.id,'name':e.student.name,'student_code':e.student.student_code}
                    for e in rows if e.student and e.student.role=='student'])

@app.post('/api/courses')
@auth_required
def create_course():
    if g.user.role != 'teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    code=str(d.get('code','')).strip().upper(); name=str(d.get('name','')).strip()
    if not code or not name: return jsonify({'error':'Course code and name are required.'}),400
    if Course.query.filter_by(code=code).first(): return jsonify({'error':'Course code already exists.'}),409
    course=Course(code=code,name=name,teacher_id=g.user.id); db.session.add(course); db.session.commit()
    return jsonify({'id':course.id,'code':course.code,'name':course.name}),201

@app.post('/api/students')
@auth_required
def create_student():
    if g.user.role != 'teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    name=str(d.get('name','')).strip(); email=str(d.get('email','')).strip().lower()
    password=str(d.get('password','')); code=str(d.get('student_code','')).strip()
    if not name or not email or len(password)<10 or not code:
        return jsonify({'error':'Name, email, student ID and a password of at least 10 characters are required.'}),400
    if User.query.filter((User.email==email)|(User.student_code==code)).first():
        return jsonify({'error':'Email or student ID already exists.'}),409
    student=User(name=name,email=email,password=generate_password_hash(password),role='student',
                 student_code=code,section=str(d.get('section','')).strip() or None)
    db.session.add(student); db.session.commit()
    return jsonify({'id':student.id,'name':student.name,'email':student.email,'student_code':student.student_code}),201

@app.post('/api/courses/assign')
@auth_required
def assign_course():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        student=db.session.get(User,int(d['student_id'])); course=db.session.get(Course,int(d['course_id']))
        if not student or student.role!='student' or not course or course.teacher_id != g.user.id: raise ValueError()
        e=Enrollment.query.filter_by(student_id=student.id,course_id=course.id).first()
        if not e: db.session.add(Enrollment(student_id=student.id,course_id=course.id)); db.session.commit()
        return jsonify({'message':'Course assigned','student_id':student.id,'course_id':course.id}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Choose a valid student and course.'}),400

@app.get('/api/attendance')
@auth_required
def get_attendance():
    q=AttendanceRecord.query
    if g.user.role=='student':
        q=q.filter_by(student_id=g.user.id)
    else:
        owned_ids=[c.id for c in Course.query.filter_by(teacher_id=g.user.id).all()]
        q=q.filter(AttendanceRecord.course_id.in_(owned_ids))
    rows=q.order_by(AttendanceRecord.class_date.desc()).limit(300).all()
    return jsonify([{'id':r.id,'student_id':r.student_id,'student_name':r.student.name,'course_id':r.course_id,'course_code':r.course.code,'course_name':r.course.name,'date':r.class_date.isoformat(),'status':r.status} for r in rows])

@app.post('/api/attendance')
@auth_required
def mark_attendance():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        student=db.session.get(User,int(d['student_id'])); course=db.session.get(Course,int(d['course_id']))
        day=datetime.date.fromisoformat(d['date']); status=d['status']
        if not student or student.role!='student' or not course or course.teacher_id != g.user.id or status not in ['present','absent','late'] or not Enrollment.query.filter_by(student_id=student.id,course_id=course.id).first(): raise ValueError()
        row=AttendanceRecord.query.filter_by(student_id=student.id,course_id=course.id,class_date=day).first()
        if row: row.status=status; row.marked_by=g.user.id
        else: db.session.add(AttendanceRecord(student_id=student.id,course_id=course.id,class_date=day,status=status,marked_by=g.user.id))
        db.session.flush()
        records=AttendanceRecord.query.filter_by(student_id=student.id,course_id=course.id).all()
        metric=Metric.query.filter_by(student_id=student.id,course_code=course.code).order_by(Metric.updated_at.desc()).first()
        if metric and records:
            metric.attendance=round(sum(1 for item in records if item.status in ('present','late'))/len(records)*100,1)
            metric.updated_at=datetime.datetime.utcnow()
        db.session.commit(); return jsonify({'message':'Attendance saved','attendance_percentage':metric.attendance if metric else None}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Provide a valid student, course, date, and status.'}),400


@app.get('/api/assignments')
@auth_required
def get_assignments():
    rows = Assignment.query.order_by(Assignment.deadline.asc()).all()

    if g.user.role == 'teacher':
        rows = [a for a in rows if a.teacher_id == g.user.id]

    now = datetime.datetime.utcnow()
    result = []

    for a in rows:
        sub = (
            Submission.query.filter_by(
                assignment_id=a.id,
                student_id=g.user.id
            ).first()
            if g.user.role == 'student'
            else None
        )

        # Students can view assignments only for courses they are enrolled in.
        # Expired assignments remain visible, but submissions are closed.
        if g.user.role == 'student':
            enrolled = Enrollment.query.filter_by(
                student_id=g.user.id,
                course_id=a.course_id
            ).first()

            if not enrolled:
                continue

        result.append({
            'id': a.id,
            'title': a.title,
            'description': a.description,
            'course_id': a.course_id,
            'course_code': a.course.code,
            'course_name': a.course.name,
            'teacher': a.teacher.name,
            'deadline': a.deadline.isoformat() + 'Z',
            'max_score': a.max_score,
            'closed': now >= a.deadline,

            'my_submission': ({
                'id': sub.id,
                'content': sub.content,
                'submitted_at': sub.submitted_at.isoformat() + 'Z',
                'score': sub.score,
                'feedback': sub.feedback,
                'files': [file_json(f) for f in sub.files]
            } if sub else None),

            'submissions': (
                [{
                    'id': x.id,
                    'student_id': x.student_id,
                    'student_name': x.student.name,
                    'content': x.content,
                    'submitted_at': x.submitted_at.isoformat() + 'Z',
                    'score': x.score,
                    'feedback': x.feedback,
                    'files': [file_json(f) for f in x.files]
                } for x in Submission.query.filter_by(
                    assignment_id=a.id
                ).all()]
                if g.user.role == 'teacher'
                else []
            )
        })

    return jsonify(result)

@app.post('/api/assignments')
@auth_required
def create_assignment():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        course=db.session.get(Course,int(d['course_id'])); deadline=datetime.datetime.fromisoformat(d['deadline'].replace('Z','+00:00')).replace(tzinfo=None)
        title=str(d['title']).strip(); max_score=float(d.get('max_score',100))
        if not course or course.teacher_id != g.user.id or not title or deadline<=datetime.datetime.utcnow() or max_score<=0: raise ValueError()
        a=Assignment(title=title,description=str(d.get('description','')),course_id=course.id,teacher_id=g.user.id,deadline=deadline,max_score=max_score)
        db.session.add(a); db.session.commit(); return jsonify({'id':a.id,'message':'Assignment created'}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Enter a title, course, future deadline, and positive maximum score.'}),400

def valid_file_signature(stream, extension):
    signatures = {'pdf': lambda b: b.startswith(b'%PDF-'),
                  'jpg': lambda b: b.startswith(b'\xff\xd8\xff'),
                  'jpeg': lambda b: b.startswith(b'\xff\xd8\xff'),
                  'png': lambda b: b.startswith(b'\x89PNG\r\n\x1a\n'),
                  'zip': lambda b: b.startswith(b'PK\x03\x04'),
                  'docx': lambda b: b.startswith(b'PK\x03\x04'),
                  'xlsx': lambda b: b.startswith(b'PK\x03\x04'),
                  'pptx': lambda b: b.startswith(b'PK\x03\x04'),
                  'odt': lambda b: b.startswith(b'PK\x03\x04'),
                  'doc': lambda b: b.startswith(b'\xd0\xcf\x11\xe0'),
                  'xls': lambda b: b.startswith(b'\xd0\xcf\x11\xe0'),
                  'ppt': lambda b: b.startswith(b'\xd0\xcf\x11\xe0')}
    if extension not in signatures: return True
    position = stream.tell(); stream.seek(0); header = stream.read(16); stream.seek(position)
    return signatures[extension](header)

def file_json(f):
    return {'id': f.id, 'name': f.original_name, 'size_bytes': f.size_bytes,
            'mime_type': f.mime_type, 'uploaded_at': f.uploaded_at.isoformat() + 'Z',
            'download_url': f'/submissions/files/{f.id}/download'}

@app.post('/api/assignments/<int:assignment_id>/submit')
@auth_required
def submit_assignment(assignment_id):
    if g.user.role != 'student':
        return jsonify({'error': 'Student access required'}), 403
    a = db.session.get(Assignment, assignment_id)
    if not a:
        return jsonify({'error': 'Assignment not found'}), 404
    if datetime.datetime.utcnow() >= a.deadline:
        return jsonify({'error': 'Deadline passed. This assignment is closed and submissions are disabled.'}), 403
    if not Enrollment.query.filter_by(student_id=g.user.id, course_id=a.course_id).first():
        return jsonify({'error': 'You are not enrolled in this course.'}), 403
    if Submission.query.filter_by(assignment_id=a.id, student_id=g.user.id).first():
        return jsonify({'error': 'You have already submitted this assignment.'}), 409
    files = [f for f in request.files.getlist('files') if f and f.filename]
    content = (request.form.get('content') or '').strip()
    if not files:
        return jsonify({'error': 'Attach at least one assignment file.'}), 400
    if len(files) > MAX_FILES:
        return jsonify({'error': f'Maximum {MAX_FILES} attachments are allowed.'}), 400
    sizes = []
    for f in files:
        f.stream.seek(0, os.SEEK_END); size = f.stream.tell(); f.stream.seek(0)
        safe = secure_filename(f.filename)
        ext = safe.rsplit('.', 1)[-1].lower() if '.' in safe else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({'error': f'File type not allowed: {f.filename}'}), 400
        if not valid_file_signature(f.stream, ext):
            return jsonify({'error': f'The file contents do not match the .{ext} format.'}), 400
        if size <= 0 or size > MAX_FILE_BYTES:
            return jsonify({'error': f'Each file must be between 1 byte and {MAX_FILE_BYTES // (1024*1024)} MB.'}), 400
        sizes.append(size)
    if sum(sizes) > MAX_TOTAL_BYTES:
        return jsonify({'error': f'Total upload cannot exceed {MAX_TOTAL_BYTES // (1024*1024)} MB.'}), 400
    row = Submission(assignment_id=a.id, student_id=g.user.id, content=content or 'File attachment submission')
    db.session.add(row); db.session.flush()
    saved = []
    try:
        for f, size in zip(files, sizes):
            original = secure_filename(f.filename)[:255] or 'attachment'
            ext = original.rsplit('.', 1)[-1].lower()
            stored = f'{uuid.uuid4().hex}.{ext}'
            f.save(UPLOAD_DIR / stored); saved.append(UPLOAD_DIR / stored)
            db.session.add(SubmissionFile(submission_id=row.id, original_name=original,
                stored_name=stored, mime_type=f.mimetype or mimetypes.guess_type(original)[0] or 'application/octet-stream',
                size_bytes=size))
        db.session.commit()
    except Exception:
        db.session.rollback()
        for path in saved: path.unlink(missing_ok=True)
        raise
    return jsonify({'message': 'Assignment submitted successfully', 'id': row.id,
                    'files': [file_json(f) for f in row.files]}), 201

@app.get('/api/submissions/files/<int:file_id>/download')
@auth_required
def download_submission_file(file_id):
    item = db.session.get(SubmissionFile, file_id)
    if not item: return jsonify({'error': 'File not found'}), 404
    submission = item.submission
    if g.user.role == 'student' and submission.student_id != g.user.id:
        return jsonify({'error': 'Access denied'}), 403
    if g.user.role == 'teacher' and submission.assignment.teacher_id != g.user.id:
        return jsonify({'error': 'Access denied'}), 403
    return send_from_directory(UPLOAD_DIR, item.stored_name, as_attachment=True,
                               download_name=item.original_name)

@app.patch('/api/submissions/<int:submission_id>/score')
@auth_required
def score_submission(submission_id):
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    row=db.session.get(Submission,submission_id)
    if not row: return jsonify({'error':'Submission not found'}),404
    if row.assignment.teacher_id != g.user.id: return jsonify({'error':'You are not assigned to this submission.'}),403
    d=request.get_json(silent=True) or {}
    try:
        score=float(d['score'])
        if score<0 or score>row.assignment.max_score: raise ValueError()
        row.score=score; row.feedback=str(d.get('feedback','')); db.session.commit()
        return jsonify({'message':'Score updated','score':row.score,'feedback':row.feedback})
    except (KeyError,ValueError,TypeError): return jsonify({'error':f'Score must be between 0 and {row.assignment.max_score}.'}),400

@app.get('/api/timetable')
@auth_required
def timetable():
    # No fabricated timetable: return only institution-published schedule records.
    return jsonify([])

@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({'error': f'Total upload exceeds {MAX_TOTAL_BYTES // (1024*1024)} MB.'}), 413

with app.app_context(): seed()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=False)
