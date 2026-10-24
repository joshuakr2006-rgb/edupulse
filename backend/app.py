import os, datetime, statistics
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

app = Flask(__name__)
CORS(app, origins=os.getenv('CLIENT_ORIGIN', '*').split(','))
uri = os.getenv('DATABASE_URL', 'sqlite:///education.db')
if uri.startswith('postgres://'): uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'change-this-before-deploying')
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

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Transparent early-warning scoring model: a practical baseline, not a clinical or final academic judgement.
def predict(m):
    risk = 0
    risk += max(0, 75 - m.attendance) * 0.45
    risk += max(0, 65 - m.assignment_avg) * 0.22
    risk += max(0, 60 - m.assessment_avg) * 0.25
    risk += max(0, 60 - m.engagement) * 0.08
    risk = round(min(100, risk), 1)
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
    """Idempotently create a rich fictional demo cohort and multiple faculty accounts."""
    import random
    db.create_all()
    for code, name in [('EICSA 316','Data Structures'),('EICSA 340','Cryptography and Network Security'),('EICSA 108','Advanced Calculus'),('EICSA 313','Database Management Systems'),('EICSA 317','Operating Systems'),('EICSA 400','Web Technologies')]:
        if not Course.query.filter_by(code=code).first(): db.session.add(Course(code=code, name=name))
    db.session.flush()
    teacher_specs = [
        ('Dr. Meera Sharma', 'teacher@demo.edu', 'Teacher@123', 'CSE General - E'),
        ('Prof. Arjun Menon', 'arjun@demo.edu', 'Teacher@123', 'CSE General - A'),
        ('Dr. Priya Iyer', 'priya@demo.edu', 'Teacher@123', 'CSE General - B'),
        ('Prof. Rahul Verma', 'rahul@demo.edu', 'Teacher@123', 'AI & Data Science'),
        ('Dr. Kavya Nair', 'kavya@demo.edu', 'Teacher@123', 'CSE General - C'),
        ('Prof. Aditya Rao', 'aditya@demo.edu', 'Teacher@123', 'CSE General - D'),
    ]
    for name, email, password, section in teacher_specs:
        if not User.query.filter_by(email=email).first():
            db.session.add(User(name=name, email=email, password=generate_password_hash(password), role='teacher', section=section))
    db.session.flush()

    # Keep the original six named accounts stable, then add a broad fictional cohort.
    base_students = [
        ('Aarav Kumar','aarav@demo.edu','AU2024001'), ('Diya Reddy','diya@demo.edu','AU2024002'),
        ('Ishaan Rao','ishaan@demo.edu','AU2024003'), ('Ananya Nair','ananya@demo.edu','AU2024004'),
        ('Kabir Shah','kabir@demo.edu','AU2024005'), ('Sara Thomas','sara@demo.edu','AU2024006'),
    ]
    first_names = ['Aditi','Advik','Akash','Amara','Arjun','Avani','Dev','Ira','Karan','Kavya','Kiara','Krish','Maya','Neel','Nisha','Om','Rhea','Rohan','Saanvi','Vihaan','Yash','Zoya','Anirudh','Bhavana','Charan','Deepa','Farhan','Gauri','Harish','Janani','Karthik','Lavanya','Manav','Nandini','Pranav','Rahul','Siddharth','Tanvi','Varun','Vidya','Akhil','Diya','Mehul','Pooja']
    last_names = ['Sharma','Reddy','Rao','Nair','Shah','Thomas','Iyer','Menon','Verma','Patel','Kumar','Joshi','Pillai','Das','Shetty','Kulkarni']
    student_specs = list(base_students)
    for i in range(7, 61):
        fn = first_names[(i * 7) % len(first_names)]
        ln = last_names[(i * 5) % len(last_names)]
        student_specs.append((f'{fn} {ln}', f'student{i:02d}@demo.edu', f'AU2024{i:04d}'))
    for name, email, code in student_specs:
        if not User.query.filter_by(email=email).first() and not User.query.filter_by(student_code=code).first():
            db.session.add(User(name=name, email=email, password=generate_password_hash('Student@123'), role='student', student_code=code, section=['CSE General - E','CSE General - A','CSE General - B','AI & Data Science'][int(code[-1]) % 4]))
    db.session.flush()

    courses = [('EICSA 316','Data Structures'), ('EICSA 340','Cryptography and Network Security'), ('EICSA 108','Advanced Calculus'), ('EICSA 313','Database Management Systems'), ('EICSA 317','Operating Systems'), ('EICSA 400','Web Technologies')]
    rng = random.Random(20261023)
    all_students = User.query.filter_by(role='student').order_by(User.id).all()
    for i, student in enumerate(all_students):
        if student.metrics:
            continue
        # Mix strong, moderate, and at-risk fictional profiles for a meaningful demo.
        if i % 7 == 0: base = (rng.randint(42,64), rng.randint(35,58), rng.randint(30,54), rng.randint(35,58))
        elif i % 4 == 0: base = (rng.randint(62,77), rng.randint(55,72), rng.randint(48,68), rng.randint(50,70))
        else: base = (rng.randint(76,98), rng.randint(68,96), rng.randint(62,94), rng.randint(65,96))
        for j, (code, course_name) in enumerate(courses):
            offsets = (j % 3) * 3
            vals = [max(25, min(100, base[k] + (offsets if k % 2 == 0 else -offsets))) for k in range(4)]
            db.session.add(Metric(student_id=student.id, course_code=code, course_name=course_name,
                attendance=vals[0], assignment_avg=vals[1], assessment_avg=vals[2], engagement=vals[3]))

    # Course enrollment records are relational and idempotent.
    db.session.flush()
    course_rows = Course.query.all()
    for student in User.query.filter_by(role='student').all():
        for course in course_rows:
            if not Enrollment.query.filter_by(student_id=student.id, course_id=course.id).first():
                db.session.add(Enrollment(student_id=student.id, course_id=course.id))
    if Activity.query.count() == 0:
        activities = [
          ('Coursera Certification Grading Assessment','Curiosity Assessment','Open','Today, 6:30 AM','EICSA 340'),
          ('Quiz-5','Objective','Submitted','Oct 14, 12:05 AM','EICSA 316'),
          ('Turing Machine? (Copy 1)','Curiosity Assessment','Open','Oct 20, 6:52 PM','EICSA 340'),
          ('Linear Bounded Automata','Curiosity Assessment','Open','Oct 20, 6:10 PM','EICSA 340')]
        for row in activities: db.session.add(Activity(title=row[0],category=row[1],status=row[2],due_label=row[3],course_code=row[4]))
    if Notice.query.count() == 0:
        db.session.add(Notice(title='Migration to New Secure Campus Wi-Fi (AUSTU-SSO)', body='Please follow the university instructions to connect to the secure campus network.'))
    db.session.commit()
    # Create initial alerts from high-risk student/course records, without duplicates.
    for m in Metric.query.all():
        p = predict(m)
        title = f'Academic early warning: {m.course_code}'
        if p['risk_level'] == 'High' and not Alert.query.filter_by(student_id=m.student_id, title=title).first():
            db.session.add(Alert(student_id=m.student_id, title=title,
                message=f'{m.student.name} may need support in {m.course_name}. ' + '; '.join(p['reasons']), severity='high'))
    db.session.commit()

@app.get('/api/health')
def health(): return jsonify({'status':'ok','service':'Smart Education Analytics API'})

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
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        student_id=int(d['student_id']); student=db.session.get(User,student_id)
        if not student or student.role!='student': raise ValueError()
        m=Metric(student_id=student_id,course_code=str(d['course_code']).strip(),course_name=str(d['course_name']).strip(),attendance=float(d['attendance']),assignment_avg=float(d['assignment_avg']),assessment_avg=float(d['assessment_avg']),engagement=float(d.get('engagement',70)))
        if any(x<0 or x>100 for x in [m.attendance,m.assignment_avg,m.assessment_avg,m.engagement]): return jsonify({'error':'Scores must be between 0 and 100'}),400
        db.session.add(m); db.session.flush(); p=predict(m)
        if p['risk_level']=='High': db.session.add(Alert(student_id=student.id,title=f'Academic early warning: {m.course_code}',message=f'{student.name} may need support in {m.course_name}. '+ '; '.join(p['reasons']),severity='high'))
        db.session.commit(); return jsonify(metric_json(m)),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Please provide a valid student and all required numeric scores.'}),400

@app.get('/api/courses')
@auth_required
def list_courses():
    rows=Course.query.order_by(Course.code).all()
    if g.user.role=='student':
        ids=[e.course_id for e in Enrollment.query.filter_by(student_id=g.user.id).all()]
        rows=[c for c in rows if c.id in ids]
    return jsonify([{'id':c.id,'code':c.code,'name':c.name} for c in rows])

@app.post('/api/courses/assign')
@auth_required
def assign_course():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        student=db.session.get(User,int(d['student_id'])); course=db.session.get(Course,int(d['course_id']))
        if not student or student.role!='student' or not course: raise ValueError()
        e=Enrollment.query.filter_by(student_id=student.id,course_id=course.id).first()
        if not e: db.session.add(Enrollment(student_id=student.id,course_id=course.id)); db.session.commit()
        return jsonify({'message':'Course assigned','student_id':student.id,'course_id':course.id}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Choose a valid student and course.'}),400

@app.get('/api/attendance')
@auth_required
def get_attendance():
    q=AttendanceRecord.query
    if g.user.role=='student': q=q.filter_by(student_id=g.user.id)
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
        if not student or student.role!='student' or not course or status not in ['present','absent','late']: raise ValueError()
        row=AttendanceRecord.query.filter_by(student_id=student.id,course_id=course.id,class_date=day).first()
        if row: row.status=status; row.marked_by=g.user.id
        else: db.session.add(AttendanceRecord(student_id=student.id,course_id=course.id,class_date=day,status=status,marked_by=g.user.id))
        db.session.commit(); return jsonify({'message':'Attendance saved'}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Provide a valid student, course, date, and status.'}),400

@app.get('/api/assignments')
@auth_required
def get_assignments():
    rows=Assignment.query.order_by(Assignment.deadline.asc()).all()
    now=datetime.datetime.utcnow()
    result=[]
    for a in rows:
        # Students cannot access an assignment at all after its deadline; teachers retain grading access.
        if g.user.role=='student' and now > a.deadline: continue
        sub=Submission.query.filter_by(assignment_id=a.id,student_id=g.user.id).first() if g.user.role=='student' else None
        if g.user.role=='student' and not Enrollment.query.filter_by(student_id=g.user.id,course_id=a.course_id).first(): continue
        result.append({'id':a.id,'title':a.title,'description':a.description,'course_id':a.course_id,'course_code':a.course.code,'course_name':a.course.name,'teacher':a.teacher.name,'deadline':a.deadline.isoformat()+'Z','max_score':a.max_score,'closed':now>a.deadline,'my_submission':({'id':sub.id,'content':sub.content,'submitted_at':sub.submitted_at.isoformat()+'Z','score':sub.score,'feedback':sub.feedback} if sub else None), 'submissions':([{'id':x.id,'student_id':x.student_id,'student_name':x.student.name,'content':x.content,'submitted_at':x.submitted_at.isoformat()+'Z','score':x.score,'feedback':x.feedback} for x in Submission.query.filter_by(assignment_id=a.id).all()] if g.user.role=='teacher' else [])})
    return jsonify(result)

@app.post('/api/assignments')
@auth_required
def create_assignment():
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    d=request.get_json(silent=True) or {}
    try:
        course=db.session.get(Course,int(d['course_id'])); deadline=datetime.datetime.fromisoformat(d['deadline'].replace('Z','+00:00')).replace(tzinfo=None)
        title=str(d['title']).strip(); max_score=float(d.get('max_score',100))
        if not course or not title or deadline<=datetime.datetime.utcnow() or max_score<=0: raise ValueError()
        a=Assignment(title=title,description=str(d.get('description','')),course_id=course.id,teacher_id=g.user.id,deadline=deadline,max_score=max_score)
        db.session.add(a); db.session.commit(); return jsonify({'id':a.id,'message':'Assignment created'}),201
    except (KeyError,ValueError,TypeError): return jsonify({'error':'Enter a title, course, future deadline, and positive maximum score.'}),400

@app.post('/api/assignments/<int:assignment_id>/submit')
@auth_required
def submit_assignment(assignment_id):
    if g.user.role!='student': return jsonify({'error':'Student access required'}),403
    a=db.session.get(Assignment,assignment_id)
    if not a: return jsonify({'error':'Assignment not found'}),404
    if datetime.datetime.utcnow()>a.deadline: return jsonify({'error':'Deadline passed. This assignment is closed and submissions are disabled.'}),403
    if not Enrollment.query.filter_by(student_id=g.user.id,course_id=a.course_id).first(): return jsonify({'error':'You are not enrolled in this course.'}),403
    if Submission.query.filter_by(assignment_id=a.id,student_id=g.user.id).first(): return jsonify({'error':'You have already submitted this assignment.'}),409
    content=(request.get_json(silent=True) or {}).get('content','').strip()
    if not content: return jsonify({'error':'Submission content is required.'}),400
    row=Submission(assignment_id=a.id,student_id=g.user.id,content=content); db.session.add(row); db.session.commit()
    return jsonify({'message':'Assignment submitted successfully','id':row.id}),201

@app.patch('/api/submissions/<int:submission_id>/score')
@auth_required
def score_submission(submission_id):
    if g.user.role!='teacher': return jsonify({'error':'Teacher access required'}),403
    row=db.session.get(Submission,submission_id)
    if not row: return jsonify({'error':'Submission not found'}),404
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
    days=['Monday','Tuesday','Wednesday','Thursday','Friday']
    slots=[('09:00 AM','10:00 AM','EICSA 316','Data Structures','Room 204'),('10:15 AM','11:15 AM','EICSA 340','Cryptography and Network Security','Lab 2'),('11:30 AM','12:30 PM','EICSA 108','Advanced Calculus','Room 108'),('01:30 PM','02:30 PM','EICSA 313','Database Management Systems','Room 305')]
    return jsonify([{'day':day,'classes':[{'start':s[0],'end':s[1],'code':s[2],'name':s[3],'room':s[4]} for s in slots[:3+(i%2)] ]} for i,day in enumerate(days)])

with app.app_context(): seed()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=False)
