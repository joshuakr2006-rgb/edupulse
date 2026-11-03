import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertTriangle, ArrowUpRight, Bell, BookOpen,
  BrainCircuit, CalendarDays, CheckCircle2, ChevronDown,
  ChevronRight, CircleHelp, ClipboardCheck, Clock3,
  GraduationCap, LayoutDashboard, LogOut, Menu, Search,
  Settings, ShieldCheck, Sparkles, TrendingUp, Users, X
} from 'lucide-react';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

async function api(path, token, options = {}) {
  const authToken = token || localStorage.getItem('edupulse_token') || '';
  const headers = {
    Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {})
  };

  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const response = await fetch(`${API}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  return data;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('edupulse_token') || '');
  const [user, setUser] = useState(null);
  const [role, setRole] = useState('student');
  const [page, setPage] = useState('Overview');
  const [data, setData] = useState(null);
  const [students, setStudents] = useState([]);
  const [timetable, setTimetable] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const [toast, setToast] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  async function load(t = token, knownUser = null) {
    const authToken = t || localStorage.getItem('edupulse_token') || '';
    if (!authToken) return;

    setLoading(true);
    setError('');

    try {
      const me = knownUser || await api('/me', authToken);
      setUser(me);
      setRole(me.role);

      const dashboard = await api('/dashboard', authToken);
      setData(dashboard);

      if (me.role === 'teacher') {
        setStudents(await api('/students', authToken));
      } else {
        setStudents([]);
      }

      setTimetable(await api('/timetable', authToken));
    } catch (e) {
      setError(
        e.status === 401
          ? 'Your session token was rejected by the server. Please check JWT_SECRET on Render and redeploy the backend.'
          : e.message
      );

      setToken('');
      setUser(null);
      setData(null);
      setStudents([]);
      setTimetable([]);
      localStorage.removeItem('edupulse_token');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem('edupulse_token');
    if (saved) load(saved);
  }, []);

  async function login(email, password, r) {
    setLoading(true);
    setError('');

    try {
      const d = await api('/auth/login', '', {
        method: 'POST',
        body: JSON.stringify({ email, password, role: r })
      });

      if (!d.token || !d.user) {
        throw new Error('Login response did not include a token and user.');
      }

      localStorage.setItem('edupulse_token', d.token);
      setToken(d.token);
      setUser(d.user);
      setRole(d.user.role);
      setPage('Overview');

      await load(d.token, d.user);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem('edupulse_token');
    sessionStorage.removeItem('edupulse_token');
    setToken('');
    setUser(null);
    setRole('student');
    setData(null);
    setStudents([]);
    setTimetable([]);
    setSearch('');
    setPage('Overview');
    setMobileNav(false);
    setShowAdd(false);
    setError('');
    setToast('');
  }

  async function updateAlert(id, status) {
    try {
      await api('/alerts/' + id, token, {
        method: 'PATCH',
        body: JSON.stringify({ status })
      });

      await load();
      setToast('Alert updated successfully');
      setTimeout(() => setToast(''), 2500);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!token || !user) {
    return <Login onLogin={login} loading={loading} error={error} />;
  }

  const nav = role === 'teacher'
    ? [
        ['Overview', LayoutDashboard],
        ['Students', Users],
        ['Early warnings', AlertTriangle],
        ['Performance analytics', TrendingUp],
        ['Assessments', ClipboardCheck],
        ['Attendance management', CalendarDays],
        ['Timetable', CalendarDays]
      ]
    : [
        ['Overview', LayoutDashboard],
        ['My learning', BookOpen],
        ['My attendance', CalendarDays],
        ['Assessments', ClipboardCheck],
        ['Recommendations', BrainCircuit],
        ['Timetable', CalendarDays]
      ];

  return (
    <div className="app-shell">
      <aside className={'sidebar ' + (mobileNav ? 'mobile-open' : '')}>
        <div className="brand">
          <div className="brand-mark"><BrainCircuit size={22} /></div>
          <div>
            <b>EduPulse</b>
            <small>SMART EDUCATION ANALYTICS</small>
          </div>
          <button className="mobile-close" onClick={() => setMobileNav(false)}>
            <X />
          </button>
        </div>

        <div className="workspace">
          <span className="workspace-dot" />
          Alliance University
          <ChevronDown size={14} />
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={'nav-item ' + (page === label ? 'active' : '')}
              onClick={() => {
                setPage(label);
                setMobileNav(false);
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === 'Early warnings' &&
                role === 'teacher' &&
                data?.stats?.open_alerts > 0 &&
                <em>{data.stats.open_alerts}</em>
              }
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={18} /></div>
            <b>Need a hand?</b>
            <p>Explore the platform and its insights.</p>
            <button onClick={() => setToast('Contact your platform administrator for assistance.')}>
              Visit help center <ChevronRight size={14} />
            </button>
          </div>

          <button
            className={'nav-item ' + (page === 'Settings' ? 'active' : '')}
            onClick={() => {
              setPage('Settings');
              setMobileNav(false);
            }}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <div className="user-mini">
            <div className="avatar">{initials(user.name)}</div>
            <div className="user-mini-text">
              <b>{user.name}</b>
              <small>{role === 'teacher' ? 'Faculty / Teacher' : 'Student'}</small>
            </div>
            <button title="Log out" onClick={logout}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="hamburger" onClick={() => setMobileNav(true)}>
            <Menu />
          </button>

          <div className="crumb">
            Workspace <ChevronRight size={14} /> <b>{page}</b>
          </div>

          <div className="top-actions">
            <div className="top-date">
              <CalendarDays size={15} /> Friday, 23 Oct 2026
            </div>

            <button
              className="icon-button"
              onClick={() => setPage(role === 'teacher' ? 'Early warnings' : 'Recommendations')}
              title="Notifications"
            >
              <Bell size={18} />
              {(data?.stats?.open_alerts || 0) > 0 && role === 'teacher' && <i />}
            </button>

            <button className="icon-button" onClick={logout} title="Log out" aria-label="Log out">
              <LogOut size={18} />
            </button>

            <div className="top-user">
              <div className="avatar">{initials(user.name)}</div>
              <div>
                <b>{user.name}</b>
                <small>{role === 'teacher' ? 'Faculty account' : 'Student account'}</small>
              </div>
              <ChevronDown size={14} />
            </div>
          </div>
        </header>

        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {role === 'teacher' ? 'FACULTY WORKSPACE' : 'YOUR LEARNING SPACE'}
                <span className="live-dot" /> LIVE OVERVIEW
              </div>

              <h1>
                {greeting()}, {user.name.split(' ')[0]} <span className="wave">✦</span>
              </h1>

              <p>
                {role === 'teacher'
                  ? 'A clear view of student progress, risk signals, and where your support matters most.'
                  : 'Your academic progress, learning activity, and next steps — all in one place.'}
              </p>
            </div>

            <div className="heading-actions">
              <button className="btn btn-light" onClick={() => setPage('Timetable')}>
                <CalendarDays size={16} /> View timetable
              </button>

              {role === 'teacher' &&
                <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
                  <span>＋</span> Add student data
                </button>
              }
            </div>
          </div>

          {error &&
            <div className="error-banner">
              <AlertTriangle size={17} />
              {error}
              <button onClick={() => setError('')}><X size={15} /></button>
            </div>
          }

          {loading && !data
            ? <div className="loading"><div className="spinner" />Loading your dashboard…</div>
            : <>
                {page === 'Overview' &&
                  <Overview data={data} role={role} setPage={setPage} updateAlert={updateAlert} />
                }

                {page === 'Students' && role === 'teacher' &&
                  <StudentsPage
                    students={students}
                    search={search}
                    setSearch={setSearch}
                    setPage={setPage}
                    token={token}
                    refresh={load}
                  />
                }

                {page === 'Early warnings' &&
                  <AlertsPage data={data} role={role} updateAlert={updateAlert} />
                }

                {page === 'Performance analytics' &&
                  <AnalyticsPage data={data} role={role} />
                }

                {page === 'Assessments' &&
                  <Assessments data={data} role={role} token={token} />
                }

                {page === 'My learning' && <Learning data={data} />}

                {(page === 'My attendance' || page === 'Attendance management') &&
                  <Attendance data={data} role={role} token={token} refresh={load} />
                }

                {page === 'Recommendations' && <Recommendations data={data} />}

                {page === 'Timetable' && <Timetable timetable={timetable} />}

                {page === 'Settings' &&
                  <AccountSettings user={user} role={role} onLogout={logout} />
                }

                <footer className="footer">
                  <span>© 2026 EduPulse · Smart Education Monitoring & Analytics</span>
                  <span><ShieldCheck size={14} /> Student data is for authorized academic support</span>
                </footer>
              </>
          }
        </div>
      </main>

      {showAdd &&
        <AddMetric
          students={students}
          token={token}
          close={() => setShowAdd(false)}
          done={async () => {
            setShowAdd(false);
            await load();
            setToast('Academic data saved and risk signals refreshed');
          }}
        />
      }

      {toast &&
        <div className="toast">
          <CheckCircle2 size={18} />
          {toast}
          <button onClick={() => setToast('')}><X size={14} /></button>
        </div>
      }
    </div>
  );
}

function Login({ onLogin, loading, error }) {
  const [role, setRole] = useState('student');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);

  function changeRole(r) {
    setRole(r);
  }

  return (
    <div className="login-page">
      <div className="login-art">
        <div className="art-grid" />

        <div className="art-brand">
          <div className="brand-mark"><BrainCircuit size={24} /></div>
          <div>
            <b>EduPulse</b>
            <small>SMART EDUCATION ANALYTICS</small>
          </div>
        </div>

        <div className="art-copy">
          <div className="pill"><Sparkles size={14} /> EARLY INSIGHTS. BETTER OUTCOMES.</div>
          <h1>Every student<br />deserves to <span>thrive.</span></h1>
          <p>
            Turn academic signals into timely support. One connected space for
            student success, teacher insights, and smarter decisions.
          </p>

          <div className="art-stat-row">
            <div><b>01</b><span>Spot risk early</span></div>
            <div><b>02</b><span>Personalize support</span></div>
            <div><b>03</b><span>Track progress</span></div>
          </div>
        </div>

        <div className="art-bottom">
          <span>✳ AI-assisted academic support</span>
          <span>Built for learning communities</span>
        </div>
      </div>

      <div className="login-side">
        <div className="login-top">
          <span>Already part of the community?</span>
          <span className="secure"><ShieldCheck size={14} /> Secure access</span>
        </div>

        <div className="login-card">
          <div className="login-icon"><GraduationCap size={25} /></div>
          <div className="eyebrow">WELCOME TO EDUPULSE</div>
          <h2>Sign in to your space</h2>
          <p className="muted">Choose your role to access your personalized dashboard.</p>

          <div className="role-switch">
            <button className={role === 'student' ? 'selected' : ''} onClick={() => changeRole('student')}>
              <BookOpen size={17} /> Student
            </button>
            <button className={role === 'teacher' ? 'selected' : ''} onClick={() => changeRole('teacher')}>
              <Users size={17} /> Teacher
            </button>
          </div>

          <form onSubmit={e => {
            e.preventDefault();
            onLogin(email, password, role);
          }}>
            <label>University email</label>
            <div className="field">
              <span>✉</span>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@university.edu"
                required
              />
            </div>

            <label>Password</label>
            <div className="field">
              <span>♙</span>
              <input
                type={show ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
              <button type="button" className="show-pass" onClick={() => setShow(!show)}>
                {show ? 'Hide' : 'Show'}
              </button>
            </div>

            {error &&
              <div className="login-error"><AlertTriangle size={15} />{error}</div>
            }

            <button className="btn btn-primary login-submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in securely'} <ChevronRight size={17} />
            </button>
          </form>

          <div className="login-privacy">
            <ShieldCheck size={14} /> Protected academic workspace
          </div>
        </div>
      </div>
    </div>
  );
}

function Overview({ data, role, setPage }) {
  if (!data) return null;

  const teacher = role === 'teacher';
  const stats = data.stats;
  const metrics = data.metrics || [];

  return <>
    <div className="stat-grid">
      {teacher ? <>
        <Stat title="Total students" value={stats.students} note="Across your cohort" icon={Users} tone="purple" />
        <Stat title="High risk" value={stats.high_risk} note="Needs timely attention" icon={AlertTriangle} tone="red" trend="Priority" />
        <Stat title="Average attendance" value={stats.avg_attendance + '%'} note="Across student cohort" icon={CalendarDays} tone="blue" />
        <Stat title="Open alerts" value={stats.open_alerts} note="Awaiting review" icon={Bell} tone="amber" />
      </> : <>
        <Stat title="Attendance" value={stats.attendance + '%'} note={stats.attendance >= 75 ? 'Above the 75% target' : 'Below the 75% target'} icon={CalendarDays} tone="purple" trend={stats.attendance >= 75 ? 'On track' : 'Attention'} />
        <Stat title="Assessment average" value={stats.assessment_avg + '%'} note="Across enrolled courses" icon={ClipboardCheck} tone="blue" />
        <Stat title="Assignment average" value={stats.assignment_avg + '%'} note="Keep building consistency" icon={BookOpen} tone="green" />
        <Stat title="Enrolled courses" value={stats.courses} note="Current semester" icon={GraduationCap} tone="amber" />
      </>}
    </div>

    <div className="dashboard-grid">
      <section className="panel performance-panel">
        <div className="panel-head">
          <div>
            <h3>{teacher ? 'Cohort performance' : 'My performance'}</h3>
            <p>{teacher ? 'Quick view of attendance across students' : 'Academic indicators across your courses'}</p>
          </div>
          <button className="text-button" onClick={() => setPage('Performance analytics')}>
            View analytics <ChevronRight size={15} />
          </button>
        </div>

        <PerformanceChart
          metrics={teacher ? metrics.filter(m => m.student_id === metrics[0]?.student_id).slice(0, 6) : metrics}
          teacher={teacher}
          students={data.students}
        />

        <div className="chart-legend">
          <span><i className="legend-purple" />Attendance</span>
          <span><i className="legend-blue" />Assessment</span>
          <span className="chart-footnote">Recorded academic indicators</span>
        </div>
      </section>

      <section className="panel risk-panel">
        <div className="panel-head">
          <div>
            <h3>{teacher ? 'AI early-warning signals' : 'Your learning signals'}</h3>
            <p>{teacher ? 'Students who may benefit from support' : 'Recommendations based on your current data'}</p>
          </div>
          <div className="spark-icon"><BrainCircuit size={18} /></div>
        </div>

        {teacher
          ? (data.students || []).filter(s => s.risk_level !== 'Low').slice(0, 4).map(s => (
              <div className="risk-row" key={s.id}>
                <div className="avatar avatar-soft">{initials(s.name)}</div>
                <div className="risk-person">
                  <b>{s.name}</b>
                  <small>{s.student_code} · {s.attendance}% attendance</small>
                </div>
                <RiskPill level={s.risk_level} />
              </div>
            ))
          : metrics.slice(0, 3).map(m => (
              <div className="risk-row" key={m.id}>
                <div className="course-icon"><BookOpen size={16} /></div>
                <div className="risk-person">
                  <b>{m.course_name}</b>
                  <small>{m.recommendation}</small>
                </div>
                <RiskPill level={m.risk_level} />
              </div>
            ))
        }

        <button className="panel-bottom-link" onClick={() => setPage(teacher ? 'Early warnings' : 'Recommendations')}>
          {teacher ? 'Review all warnings' : 'See all recommendations'} <ChevronRight size={15} />
        </button>
      </section>
    </div>

    <div className="lower-grid">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h3>{teacher ? 'Students needing attention' : 'Recent learning activity'}</h3>
            <p>{teacher ? 'Prioritize outreach using the risk signals' : 'Assignments, quizzes, and course activity'}</p>
          </div>
          <button className="text-button" onClick={() => setPage(teacher ? 'Students' : 'Assessments')}>
            View all <ChevronRight size={15} />
          </button>
        </div>

        {teacher
          ? <StudentTable students={(data.students || []).filter(s => s.risk_level !== 'Low').slice(0, 4)} />
          : <ActivityList activities={data.activities} />
        }
      </section>

      <section className="panel notice-panel">
        <div className="panel-head">
          <div>
            <h3>{teacher ? 'Recent alerts' : 'University notices'}</h3>
            <p>{teacher ? 'Stay ahead of emerging concerns' : 'Important updates for your learning'}</p>
          </div>
          <div className="notice-icon"><Bell size={17} /></div>
        </div>

        {teacher
          ? (data.alerts || []).slice(0, 3).map(a => (
              <div className="notice-row" key={a.id}>
                <div className={'notice-dot ' + a.severity} />
                <div>
                  <b>{a.title}</b>
                  <p>{a.message}</p>
                  <small>{a.status} · {new Date(a.created_at).toLocaleDateString()}</small>
                </div>
              </div>
            ))
          : (data.notices || []).map(n => (
              <div className="notice-row" key={n.id}>
                <div className="notice-dot info" />
                <div>
                  <b>{n.title}</b>
                  <p>{n.body}</p>
                  <small>University notice</small>
                </div>
              </div>
            ))
        }
      </section>
    </div>

    <section className="panel activity-panel">
      <div className="panel-head">
        <div>
          <h3>Learning activity</h3>
          <p>Recent and upcoming assessments in your workspace</p>
        </div>
        <button className="text-button" onClick={() => setPage('Assessments')}>
          View all activities <ChevronRight size={15} />
        </button>
      </div>
      <ActivityList activities={data.activities} />
    </section>
  </>;
}

function Stat({ title, value, note, icon: Icon, tone, trend }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{title}</span>
        <div className={'stat-icon ' + tone}><Icon size={18} /></div>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-bottom">
        <span>{note}</span>
        {trend &&
          <span className={'trend ' + (trend === 'Priority' || trend === 'Attention' ? 'trend-warn' : '')}>
            <ArrowUpRight size={13} />{trend}
          </span>
        }
      </div>
    </div>
  );
}

function PerformanceChart({ metrics = [], teacher, students = [] }) {
  const items = teacher
    ? (students || []).slice(0, 6).map(s => ({
        label: s.name.split(' ')[0],
        attendance: s.attendance,
        assessment: s.assessment_avg
      }))
    : metrics.map(m => ({
        label: m.course_code,
        attendance: m.attendance,
        assessment: m.assessment_avg
      }));

  return (
    <div className="bar-chart">
      {items.length
        ? items.map((m, i) => (
            <div className="bar-group" key={m.label + i}>
              <div className="bars">
                <div className="bar-track">
                  <div className="bar bar-purple" style={{ height: Math.max(4, m.attendance) + '%' }} title={'Attendance ' + m.attendance + '%'} />
                </div>
                <div className="bar-track">
                  <div className="bar bar-blue" style={{ height: Math.max(4, m.assessment) + '%' }} title={'Assessment ' + m.assessment + '%'} />
                </div>
              </div>
              <span className="bar-label">{m.label}</span>
            </div>
          ))
        : <div className="empty">No academic metrics yet.</div>
      }
    </div>
  );
}

function ActivityList({ activities = [] }) {
  return (
    <div className="activity-list">
      {(activities || []).map(a => (
        <div className="activity-row" key={a.id}>
          <div className="activity-type"><Sparkles size={17} /></div>
          <div className="activity-title">
            <b>{a.title}</b>
            <small>{a.category} · {a.course_code}</small>
          </div>
          <div className="activity-due"><Clock3 size={14} />{a.due_label}</div>
          <span className={'status-pill ' + (a.status === 'Submitted' ? 'submitted' : 'open')}>
            {a.status}
          </span>
          <ChevronRight size={16} className="activity-chevron" />
        </div>
      ))}
    </div>
  );
}

function RiskPill({ level }) {
  return (
    <span className={'risk-pill ' + (level || 'Low').toLowerCase()}>
      <i />{level || 'Low'} risk
    </span>
  );
}

function StudentTable({ students = [] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Student</th>
            <th>Attendance</th>
            <th>Assessment</th>
            <th>Risk level</th>
          </tr>
        </thead>
        <tbody>
          {students.map(s => (
            <tr key={s.id}>
              <td>
                <div className="table-person">
                  <div className="avatar avatar-soft">{initials(s.name)}</div>
                  <div>
                    <b>{s.name}</b>
                    <small>{s.student_code}</small>
                  </div>
                </div>
              </td>
              <td>
                <div className="progress-cell">
                  <span>{s.attendance}%</span>
                  <div className="mini-progress"><i style={{ width: s.attendance + '%' }} /></div>
                </div>
              </td>
              <td>{s.assessment_avg}%</td>
              <td><RiskPill level={s.risk_level} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {!students.length && <div className="empty">No students to display.</div>}
    </div>
  );
}

function StudentsPage({ students, search, setSearch, setPage, token, refresh }) {
  const [form, setForm] = useState({
    name: '', email: '', student_code: '', password: '', section: ''
  });
  const [courseId, setCourseId] = useState('');
  const [courses, setCourses] = useState([]);
  const [metricForm, setMetricForm] = useState({
    student_id: '', course_id: '', attendance: 80,
    assignment_avg: 0, assessment_avg: 0, engagement: 50
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api('/courses', token).then(setCourses).catch(e => setError(e.message));
  }, [token]);

  const filtered = students.filter(s =>
    (s.name + ' ' + s.student_code + ' ' + s.email).toLowerCase().includes(search.toLowerCase())
  );

  async function addMetric(e) {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      const course = courses.find(c => String(c.id) === String(metricForm.course_id));
      if (!course) throw new Error('Choose a course.');

      await api('/metrics', token, {
        method: 'POST',
        body: JSON.stringify({
          student_id: Number(metricForm.student_id),
          course_id: Number(metricForm.course_id),
          course_code: course.code,
          course_name: course.name,
          attendance: Number(metricForm.attendance),
          assignment_avg: Number(metricForm.assignment_avg),
          assessment_avg: Number(metricForm.assessment_avg),
          engagement: Number(metricForm.engagement)
        })
      });

      setMessage('Academic indicators saved and risk prediction refreshed.');
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function addStudent(e) {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      const student = await api('/students', token, {
        method: 'POST',
        body: JSON.stringify(form)
      });

      if (courseId) {
        await api('/courses/assign', token, {
          method: 'POST',
          body: JSON.stringify({
            student_id: student.id,
            course_id: Number(courseId)
          })
        });
      }

      setForm({ name: '', email: '', student_code: '', password: '', section: '' });
      setCourseId('');
      setMessage('Student account created. Ask the student to sign in using the credentials provided securely.');
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return <>
    <div className="section-intro">
      <div>
        <h2>Student management</h2>
        <p>Create student accounts and review enrolled learners.</p>
      </div>
    </div>

    {error && <div className="login-error">{error}</div>}
    {message && <p role="status">{message}</p>}

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>Create student account</h3>
          <p>Use an institutional email and assign an initial course if required.</p>
        </div>
      </div>

      <form className="metric-form" onSubmit={addStudent}>
        <div className="form-two">
          <label>Full name
            <input required value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </label>
          <label>Institutional email
            <input type="email" required value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </label>
          <label>Student ID
            <input required value={form.student_code} onChange={e => setForm(p => ({ ...p, student_code: e.target.value }))} />
          </label>
          <label>Temporary password (10+ characters)
            <input type="password" minLength="10" required value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} />
          </label>
          <label>Section
            <input value={form.section} onChange={e => setForm(p => ({ ...p, section: e.target.value }))} />
          </label>
          <label>Initial course
            <select value={courseId} onChange={e => setCourseId(e.target.value)}>
              <option value="">Do not assign yet</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
            </select>
          </label>
        </div>
        <button className="btn btn-primary" type="submit">Create student</button>
      </form>
    </section>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>Record academic indicators</h3>
          <p>Save validated marks and attendance for the ML early-warning assessment.</p>
        </div>
      </div>

      <form className="metric-form" onSubmit={addMetric}>
        <div className="form-two">
          <label>Student
            <select required value={metricForm.student_id} onChange={e => setMetricForm(p => ({ ...p, student_id: e.target.value }))}>
              <option value="">Select student</option>
              {students.map(st => <option key={st.id} value={st.id}>{st.name} — {st.student_code}</option>)}
            </select>
          </label>
          <label>Course
            <select required value={metricForm.course_id} onChange={e => setMetricForm(p => ({ ...p, course_id: e.target.value }))}>
              <option value="">Select course</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
            </select>
          </label>
          <label>Attendance %
            <input type="number" min="0" max="100" step="0.1" required value={metricForm.attendance} onChange={e => setMetricForm(p => ({ ...p, attendance: e.target.value }))} />
          </label>
          <label>Assignment average %
            <input type="number" min="0" max="100" step="0.1" required value={metricForm.assignment_avg} onChange={e => setMetricForm(p => ({ ...p, assignment_avg: e.target.value }))} />
          </label>
          <label>Assessment average %
            <input type="number" min="0" max="100" step="0.1" required value={metricForm.assessment_avg} onChange={e => setMetricForm(p => ({ ...p, assessment_avg: e.target.value }))} />
          </label>
          <label>Engagement %
            <input type="number" min="0" max="100" step="0.1" required value={metricForm.engagement} onChange={e => setMetricForm(p => ({ ...p, engagement: e.target.value }))} />
          </label>
        </div>
        <button className="btn btn-primary" type="submit" disabled={!students.length || !courses.length}>
          Save indicators and predict risk
        </button>
      </form>
    </section>

    <div className="toolbar">
      <div className="searchbox">
        <Search size={17} />
        <input placeholder="Search by student name or ID…" value={search} onChange={e => setSearch(e.target.value)} />
      </div>
      <span className="muted">{filtered.length} students</span>
    </div>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>Student directory</h3>
          <p>Academic indicators and support needs</p>
        </div>
      </div>
      <StudentTable students={filtered} />
      <div className="student-cards">
        {filtered.map(s => (
          <button className="student-card" key={s.id} onClick={() => setPage('Performance analytics')}>
            <div className="avatar">{initials(s.name)}</div>
            <b>{s.name}</b>
            <small>{s.student_code}</small>
            <RiskPill level={s.risk_level} />
            <ChevronRight size={16} />
          </button>
        ))}
      </div>
    </section>
  </>;
}

function AlertsPage({ data, role, updateAlert }) {
  const alerts = data?.alerts || [];

  return <>
    <div className="section-intro">
      <div>
        <h2>{role === 'teacher' ? 'Early-warning inbox' : 'Your academic alerts'}</h2>
        <p>
          {role === 'teacher'
            ? 'AI-assisted signals that may need timely faculty attention. Review context before deciding on an intervention.'
            : 'Academic signals and reminders to help you get support early.'}
        </p>
      </div>
      <div className="notice-icon"><Bell size={19} /></div>
    </div>

    <div className="alert-summary">
      <div><b>{alerts.filter(a => a.status === 'New').length}</b><span>New</span></div>
      <div><b>{alerts.filter(a => a.status === 'Reviewed').length}</b><span>Reviewed</span></div>
      <div><b>{alerts.filter(a => a.status === 'Resolved').length}</b><span>Resolved</span></div>
    </div>

    <div className="alert-list">
      {alerts.map(a => (
        <article className="alert-card" key={a.id}>
          <div className={'alert-mark ' + a.severity}><AlertTriangle size={20} /></div>
          <div className="alert-content">
            <div className="alert-title-line">
              <h3>{a.title}</h3>
              <RiskPill level={a.severity === 'high' ? 'High' : a.severity === 'medium' ? 'Moderate' : 'Low'} />
            </div>

            {role === 'teacher' && <div className="alert-student">{a.student_name} · {a.student_code}</div>}
            <p>{a.message}</p>

            <div className="alert-meta">
              <span><Clock3 size={13} />{new Date(a.created_at).toLocaleString()}</span>
              <span className={'status-pill ' + (a.status === 'Resolved' ? 'submitted' : 'open')}>{a.status}</span>
            </div>
          </div>

          {role === 'teacher' &&
            <div className="alert-actions">
              {a.status === 'New' &&
                <button className="btn btn-light btn-small" onClick={() => updateAlert(a.id, 'Reviewed')}>
                  Mark reviewed
                </button>
              }
              {a.status !== 'Resolved' &&
                <button className="btn btn-primary btn-small" onClick={() => updateAlert(a.id, 'Resolved')}>
                  <CheckCircle2 size={14} /> Resolve
                </button>
              }
            </div>
          }
        </article>
      ))}

      {!alerts.length &&
        <div className="empty panel">No alerts right now. New warning signals will appear here as academic data is updated.</div>
      }
    </div>

    <div className="disclaimer">
      <BrainCircuit size={17} />
      <div>
        <b>How to interpret these signals</b>
        <p>
          Risk scores are screening aids based on attendance, assessments, assignments,
          and engagement. They are not definitive judgments. Review the underlying data
          and speak with the student before taking action.
        </p>
      </div>
    </div>
  </>;
}

function AnalyticsPage({ data, role }) {
  const teacher = role === 'teacher';
  const students = data?.students || [];
  const metrics = data?.metrics || [];

  return <>
    <div className="section-intro">
      <div>
        <h2>Performance analytics</h2>
        <p>
          {teacher
            ? 'Explore cohort-level indicators and compare students who may need support.'
            : 'Review your course indicators and the signals behind your progress.'}
        </p>
      </div>
      <div className="spark-icon large"><BrainCircuit size={22} /></div>
    </div>

    <div className="stat-grid">
      <Stat title={teacher ? 'Cohort attendance' : 'Average attendance'} value={(teacher ? data?.stats?.avg_attendance : data?.stats?.attendance) + '%'} note="Attendance indicator" icon={CalendarDays} tone="purple" />
      <Stat title="Assessment average" value={(teacher ? avg(students, 'assessment_avg') : data?.stats?.assessment_avg) + '%'} note="Latest available scores" icon={ClipboardCheck} tone="blue" />
      <Stat title="High risk" value={teacher ? data?.stats?.high_risk : metrics.filter(m => m.risk_level === 'High').length} note="Requires review" icon={AlertTriangle} tone="red" />
      <Stat title="Learning signals" value={metrics.length} note="Course-level records" icon={Activity} tone="green" />
    </div>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>{teacher ? 'Cohort risk distribution' : 'Course performance breakdown'}</h3>
          <p>Use this as a prompt for review, not as a final decision about a learner.</p>
        </div>
      </div>

      {teacher
        ? <div className="distribution">
            {['High', 'Moderate', 'Low'].map(l => {
              const n = students.filter(s => s.risk_level === l).length;
              return (
                <div className="dist-row" key={l}>
                  <div className="dist-label"><RiskPill level={l} /><span>{n} students</span></div>
                  <div className="dist-track"><i className={'dist-' + l.toLowerCase()} style={{ width: (students.length ? n / students.length * 100 : 0) + '%' }} /></div>
                  <b>{students.length ? Math.round(n / students.length * 100) : 0}%</b>
                </div>
              );
            })}
          </div>
        : <StudentTable students={metrics.map(m => ({
            id: m.id,
            name: m.course_name,
            student_code: m.course_code,
            attendance: m.attendance,
            assessment_avg: m.assessment_avg,
            risk_level: m.risk_level
          }))} />
      }
    </section>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>{teacher ? 'Student performance table' : 'Your learning indicators'}</h3>
          <p>Attendance, assignment, assessment and AI risk signals</p>
        </div>
      </div>

      {teacher
        ? <StudentTable students={students} />
        : <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Attendance</th>
                  <th>Assignment</th>
                  <th>Assessment</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map(m => (
                  <tr key={m.id}>
                    <td><b>{m.course_name}</b><small className="block">{m.course_code}</small></td>
                    <td>{m.attendance}%</td>
                    <td>{m.assignment_avg}%</td>
                    <td>{m.assessment_avg}%</td>
                    <td><RiskPill level={m.risk_level} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
      }
    </section>
  </>;
}

function Assessments({ data, role, token }) {
  const [items, setItems] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const [form, setForm] = useState({
    title: '',
    description: '',
    course_id: '',
    deadline: '',
    max_score: 100
  });

  const [answers, setAnswers] = useState({});
  const [selectedFiles, setSelectedFiles] = useState({});
  const [scores, setScores] = useState({});
  const [courseDraft, setCourseDraft] = useState({ code: '', name: '' });

  async function load() {
    setLoading(true);
    setError('');

    try {
      const assignments = await api('/assignments', token);
      setItems(Array.isArray(assignments) ? assignments : assignments.value || []);

      if (role === 'teacher') {
        const result = await api('/courses', token);
        setCourses(Array.isArray(result) ? result : result.value || []);
      }
    } catch (e) {
      setError(e.message || 'Could not load assignments.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [token, role]);

  async function createCourse(e) {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      await api('/courses', token, {
        method: 'POST',
        body: JSON.stringify(courseDraft)
      });

      setCourseDraft({ code: '', name: '' });
      setMessage('Course created.');
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function create(e) {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      await api('/assignments', token, {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          course_id: Number(form.course_id),
          max_score: Number(form.max_score),
          deadline: new Date(form.deadline).toISOString()
        })
      });

      setForm({
        title: '',
        description: '',
        course_id: '',
        deadline: '',
        max_score: 100
      });

      setMessage('Assignment created successfully.');
      await load();
    } catch (e) {
      setError(e.message || 'Could not create assignment.');
    }
  }

  async function submit(assignmentId) {
    setError('');
    setMessage('');

    try {
      const files = selectedFiles[assignmentId] || [];

      if (!files.length) throw new Error('Please attach at least one file.');
      if (files.length > 5) throw new Error('You can upload up to 5 files.');

      if (files.some(file => file.size > 20 * 1024 * 1024)) {
        throw new Error('Each file must be 20 MB or smaller.');
      }

      if (files.reduce((sum, file) => sum + file.size, 0) > 50 * 1024 * 1024) {
        throw new Error('Combined attachments cannot exceed 50 MB.');
      }

      const formData = new FormData();
      formData.append('content', answers[assignmentId] || '');

      (selectedFiles[assignmentId] || []).forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch(`${API}/assignments/${assignmentId}/submit`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token || localStorage.getItem('edupulse_token') || ''}`
        },
        body: formData
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(result.error || `Upload failed (${response.status})`);
      }

      setMessage('Submission saved successfully.');
      setSelectedFiles(p => ({ ...p, [assignmentId]: [] }));
      setAnswers(p => ({ ...p, [assignmentId]: '' }));

      await load();
    } catch (e) {
      setError(e.message || 'Submission failed.');
    }
  }

  async function grade(submissionId, maxScore) {
    const item = scores[submissionId] || {};

    setError('');
    setMessage('');

    if (
      item.score === '' ||
      item.score == null ||
      !Number.isFinite(Number(item.score)) ||
      Number(item.score) < 0 ||
      Number(item.score) > Number(maxScore)
    ) {
      setError(`Enter a numeric score from 0 to ${maxScore}.`);
      return;
    }

    try {
      setScores(current => ({
        ...current,
        [submissionId]: {
          ...current[submissionId],
          saving: true
        }
      }));

      await api(`/submissions/${submissionId}/score`, token, {
        method: 'PATCH',
        body: JSON.stringify({
          score: Number(item.score),
          feedback: item.feedback || ''
        })
      });

      await load();

      setMessage(
        '✓ Score and feedback saved successfully! The student\'s marks and feedback have been updated.'
      );

      setScores(current => ({
        ...current,
        [submissionId]: {
          ...current[submissionId],
          saving: false
        }
      }));
    } catch (e) {
      setScores(current => ({
        ...current,
        [submissionId]: {
          ...current[submissionId],
          saving: false
        }
      }));

      setError(e.message || 'Unable to save the score. Please try again.');
    }
  }

  async function downloadAttachment(file) {
    try {
      const response = await fetch(`${API}${file.download_url}`, {
        headers: {
          Authorization: `Bearer ${token || localStorage.getItem('edupulse_token') || ''}`
        }
      });

      if (!response.ok) {
        throw new Error('Could not download attachment.');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = file.name;
      link.click();

      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  }

  const allowedFiles = '.pdf,.doc,.docx,.jpg,.jpeg,.png,.txt,.rtf,.odt,.xls,.xlsx,.csv,.ppt,.pptx,.zip';

  const fieldStyle = {
    padding: 10,
    border: '1px solid #ddd',
    borderRadius: 8,
    width: '100%',
    margin: '5px 0 12px'
  };

  const buttonStyle = {
    padding: '9px 14px',
    border: 0,
    borderRadius: 8,
    cursor: 'pointer',
    background: '#176B5B',
    color: 'white'
  };

  return <>
    <div className="section-intro">
      <div>
        <h2>Assignments</h2>
        <p>Create coursework, submit answers before deadlines, and manage individual scores.</p>
      </div>
      <div className="course-icon big"><ClipboardCheck size={22} /></div>
    </div>

    {error &&
      <div className="login-error" role="alert">{error}</div>
    }

    {message &&
      <div
        role="status"
        aria-live="polite"
        style={{
          background: '#e8f7ef',
          color: '#176b45',
          border: '1px solid #b8e5cc',
          padding: '13px 16px',
          borderRadius: 10,
          margin: '12px 0 18px',
          fontSize: 14,
          fontWeight: 600
        }}
      >
        {message}
      </div>
    }

    {loading && <p>Loading assignments…</p>}

    {role === 'teacher' &&
      <section className="panel" style={{ padding: 20, marginBottom: 20 }}>
        <h3>Create course</h3>

        <form
          onSubmit={createCourse}
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 2fr auto',
            gap: 8,
            marginBottom: 20
          }}
        >
          <input
            style={fieldStyle}
            placeholder="Course code"
            required
            value={courseDraft.code}
            onChange={e => setCourseDraft(p => ({ ...p, code: e.target.value }))}
          />

          <input
            style={fieldStyle}
            placeholder="Course name"
            required
            value={courseDraft.name}
            onChange={e => setCourseDraft(p => ({ ...p, name: e.target.value }))}
          />

          <button style={buttonStyle} type="submit">Add course</button>
        </form>

        <h3>Create assignment</h3>

        <form onSubmit={create}>
          <label>
            Title
            <input
              style={fieldStyle}
              required
              value={form.title}
              onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            />
          </label>

          <label>
            Description
            <textarea
              style={fieldStyle}
              value={form.description}
              onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            />
          </label>

          <label>
            Course
            <select
              style={fieldStyle}
              required
              value={form.course_id}
              onChange={e => setForm(p => ({ ...p, course_id: e.target.value }))}
            >
              <option value="">Choose a course</option>
              {courses.map(c => (
                <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
              ))}
            </select>
          </label>

          <label>
            Deadline
            <input
              style={fieldStyle}
              type="datetime-local"
              required
              min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
              value={form.deadline}
              onChange={e => setForm(p => ({ ...p, deadline: e.target.value }))}
            />
          </label>

          <label>
            Maximum score
            <input
              style={fieldStyle}
              type="number"
              min="1"
              required
              value={form.max_score}
              onChange={e => setForm(p => ({ ...p, max_score: e.target.value }))}
            />
          </label>

          <button style={buttonStyle} type="submit">Create assignment</button>
        </form>
      </section>
    }

    <section className="panel" style={{ padding: 20 }}>
      <div className="panel-head">
        <div>
          <h3>Assignments and submissions</h3>
          <p>{items.length} assignments available to this account</p>
        </div>
      </div>

      {!loading && items.length === 0 &&
        <p>No assignments are currently available.</p>
      }

      {items.map(a => (
        <article key={a.id} style={{ borderTop: '1px solid #eee', padding: '18px 0' }}>
          <h3>{a.title}</h3>
          <p>{a.course_code} — {a.course_name}</p>
          <p>{a.description}</p>

          <p>
            <b>Deadline:</b> {new Date(a.deadline).toLocaleString()}

            {a.closed &&
              <span
                style={{
                  display: 'inline-block',
                  marginLeft: 10,
                  padding: '4px 9px',
                  borderRadius: 999,
                  background: '#f1f3f5',
                  color: '#626b75',
                  border: '1px solid #d9dee3',
                  fontSize: 12,
                  fontWeight: 700,
                  verticalAlign: 'middle'
                }}
              >
                Overdue
              </span>
            }
          </p>

          <p><b>Maximum score:</b> {a.max_score}</p>

          {role === 'student' &&
            <>
              {a.my_submission
                ? <div>
                    <p>Submitted: {new Date(a.my_submission.submitted_at).toLocaleString()}</p>
                    <p><b>Score:</b> {a.my_submission.score ?? 'Not graded yet'}</p>

                    {a.my_submission.feedback &&
                      <p>Feedback: {a.my_submission.feedback}</p>
                    }

                    {(a.my_submission.files || []).map(file => (
                      <p key={file.id}>
                        📎 {file.name} · {(file.size_bytes / 1024 / 1024).toFixed(2)} MB
                        {' '}
                        <button type="button" onClick={() => downloadAttachment(file)}>
                          Download
                        </button>
                      </p>
                    ))}
                  </div>
                : <form onSubmit={e => {
                    e.preventDefault();
                    submit(a.id);
                  }}>
                    <label>
                      Optional note
                      <textarea
                        style={fieldStyle}
                        disabled={a.closed}
                        value={answers[a.id] || ''}
                        onChange={e => setAnswers(p => ({ ...p, [a.id]: e.target.value }))}
                      />
                    </label>

                    <label>
                      Attach assignment files (up to 5 files, 20 MB each, 50 MB total)
                      <input
                        style={fieldStyle}
                        type="file"
                        multiple
                        accept={allowedFiles}
                        disabled={a.closed}
                        onChange={e => setSelectedFiles(p => ({
                          ...p,
                          [a.id]: Array.from(e.target.files || [])
                        }))}
                      />
                    </label>

                    {(selectedFiles[a.id] || []).map((f, i) => (
                      <p key={`${f.name}-${i}`} style={{ fontSize: 11 }}>
                        📎 {f.name} · {(f.size / 1024 / 1024).toFixed(2)} MB
                        {' '}
                        <button
                          type="button"
                          onClick={() => setSelectedFiles(p => ({
                            ...p,
                            [a.id]: (p[a.id] || []).filter((_, idx) => idx !== i)
                          }))}
                        >
                          Remove
                        </button>
                      </p>
                    ))}

                    <button
                      type="submit"
                      style={{
                        ...buttonStyle,
                        ...(a.closed
                          ? {
                              background: '#e5e7eb',
                              color: '#6b7280',
                              border: '1px solid #d1d5db',
                              cursor: 'not-allowed'
                            }
                          : {})
                      }}
                      disabled={a.closed || loading}
                    >
                      {a.closed ? 'Deadline passed' : 'Upload and submit'}
                    </button>
                  </form>
              }
            </>
          }

          {role === 'teacher' &&
            (a.submissions || []).map(s => (
              <div key={s.id} style={{ borderTop: '1px solid #eee', padding: 12 }}>
                <b>{s.student_name}</b>
                <p style={{ whiteSpace: 'pre-wrap' }}>{s.content}</p>

                {(s.files || []).map(file => (
                  <p key={file.id}>
                    📎 {file.name} · {(file.size_bytes / 1024 / 1024).toFixed(2)} MB
                    {' '}
                    <button type="button" onClick={() => downloadAttachment(file)}>
                      Download attachment
                    </button>
                  </p>
                ))}

                <label>
                  Score
                  <input
                    style={fieldStyle}
                    type="number"
                    min="0"
                    max={a.max_score}
                    value={scores[s.id]?.score ?? s.score ?? ''}
                    onChange={e => setScores(p => ({
                      ...p,
                      [s.id]: {
                        ...p[s.id],
                        score: e.target.value,
                        feedback: p[s.id]?.feedback ?? s.feedback ?? ''
                      }
                    }))}
                  />
                </label>

                <label>
                  Feedback
                  <textarea
                    style={fieldStyle}
                    value={scores[s.id]?.feedback ?? s.feedback ?? ''}
                    onChange={e => setScores(p => ({
                      ...p,
                      [s.id]: {
                        ...p[s.id],
                        score: p[s.id]?.score ?? s.score ?? '',
                        feedback: e.target.value
                      }
                    }))}
                  />
                </label>

                <button
                  type="button"
                  style={{
                    ...buttonStyle,
                    opacity: scores[s.id]?.saving ? 0.65 : 1,
                    cursor: scores[s.id]?.saving ? 'not-allowed' : 'pointer'
                  }}
                  disabled={Boolean(scores[s.id]?.saving)}
                  onClick={() => grade(s.id, a.max_score)}
                >
                  {scores[s.id]?.saving ? 'Saving...' : 'Save score'}
                </button>
              </div>
            ))
          }
        </article>
      ))}
    </section>
  </>;
}

function Learning({ data }) {
  return <>
    <div className="section-intro">
      <div>
        <h2>My learning</h2>
        <p>Your enrolled courses, current performance, and suggested next steps.</p>
      </div>
      <div className="course-icon big"><BookOpen size={22} /></div>
    </div>

    <div className="course-grid">
      {(data?.metrics || []).map(m => (
        <div className="course-card" key={m.id}>
          <div className="course-card-top">
            <div className="course-icon"><BookOpen size={18} /></div>
            <RiskPill level={m.risk_level} />
          </div>

          <small>{m.course_code}</small>
          <h3>{m.course_name}</h3>

          <div className="course-stats">
            <span>Attendance <b>{m.attendance}%</b></span>
            <span>Assessment <b>{m.assessment_avg}%</b></span>
          </div>

          <div className="mini-progress"><i style={{ width: m.assessment_avg + '%' }} /></div>
          <p>{m.recommendation}</p>
        </div>
      ))}
    </div>
  </>;
}

function Attendance({ data, role, token, refresh }) {
  const [courses, setCourses] = useState([]);
  const [roster, setRoster] = useState([]);
  const [records, setRecords] = useState([]);
  const [courseId, setCourseId] = useState('');
  const [classDate, setClassDate] = useState(new Date().toISOString().slice(0, 10));
  const [statuses, setStatuses] = useState({});
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const metrics = data?.metrics || [];

  async function loadTeacherAttendance() {
    try {
      const [c, r] = await Promise.all([
        api('/courses', token),
        api('/attendance', token)
      ]);

      setCourses(c || []);
      setRecords(r || []);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    if (role === 'teacher') loadTeacherAttendance();
  }, [role, token]);

  useEffect(() => {
    if (role === 'teacher' && courseId) {
      api(`/courses/${courseId}/students`, token)
        .then(setRoster)
        .catch(e => setError(e.message));
    } else {
      setRoster([]);
    }
  }, [courseId, role, token]);

  useEffect(() => {
    if (!courseId) return;

    const existing = {};

    records
      .filter(r => String(r.course_id) === String(courseId) && r.date === classDate)
      .forEach(r => {
        existing[r.student_id] = r.status;
      });

    setStatuses(existing);
  }, [records, courseId, classDate]);

  async function saveAttendance(e) {
    e.preventDefault();
    setError('');
    setNotice('');

    if (!courseId || !roster.length) {
      setError('Select a course with enrolled students.');
      return;
    }

    if (roster.some(student => !statuses[student.id])) {
      setError('Choose a status for every student before saving.');
      return;
    }

    try {
      for (const student of roster) {
        const status = statuses[student.id];

        await api('/attendance', token, {
          method: 'POST',
          body: JSON.stringify({
            student_id: student.id,
            course_id: Number(courseId),
            date: classDate,
            status
          })
        });
      }

      setNotice(`Attendance saved for ${roster.length} students.`);
      await loadTeacherAttendance();
    } catch (e) {
      setError(e.message);
    }
  }

  if (role === 'teacher') {
    return <>
      <div className="section-intro">
        <div>
          <h2>Attendance entry</h2>
          <p>Record and correct attendance for students in your courses.</p>
        </div>
        <div className="course-icon big"><CalendarDays size={22} /></div>
      </div>

      {error && <div className="login-error">{error}</div>}
      {notice && <p role="status">{notice}</p>}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h3>Mark class attendance</h3>
            <p>Choose a course and date, then set each student's status.</p>
          </div>
        </div>

        <form onSubmit={saveAttendance} className="metric-form">
          <label>
            Course
            <select
              required
              value={courseId}
              onChange={e => {
                setCourseId(e.target.value);
                setStatuses({});
              }}
            >
              <option value="">Select course</option>
              {courses.map(c => (
                <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
              ))}
            </select>
          </label>

          <label>
            Class date
            <input type="date" required value={classDate} onChange={e => setClassDate(e.target.value)} />
          </label>

          {roster.map(student => (
            <div key={student.id} className="attendance-line" style={{ gridTemplateColumns: '1fr 180px' }}>
              <div className="attendance-course">
                <b>{student.name}</b>
                <small>{student.student_code}</small>
              </div>

              <select
                required
                value={statuses[student.id] || ''}
                onChange={e => setStatuses(p => ({ ...p, [student.id]: e.target.value }))}
              >
                <option value="">Choose status</option>
                <option value="present">Present</option>
                <option value="absent">Absent</option>
                <option value="late">Late</option>
              </select>
            </div>
          ))}

          {courseId && roster.length === 0 &&
            <p className="empty">No enrolled students are listed for this course.</p>
          }

          <button className="btn btn-primary" type="submit" disabled={!courseId || !roster.length}>
            Save attendance
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h3>Recent attendance records</h3>
            <p>Latest saved attendance entries</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Student</th><th>Course</th><th>Date</th><th>Status</th></tr>
            </thead>
            <tbody>
              {records.slice(0, 100).map(r => (
                <tr key={r.id}>
                  <td>{r.student_name}</td>
                  <td>{r.course_code}</td>
                  <td>{r.date}</td>
                  <td>{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>;
  }

  return <>
    <div className="section-intro">
      <div>
        <h2>My attendance</h2>
        <p>Monitor course-wise attendance and stay aware of the 75% target.</p>
      </div>
      <div className="course-icon big"><CalendarDays size={22} /></div>
    </div>

    <div className="attendance-banner">
      <div>
        <span>Average attendance</span>
        <h2>{data?.stats?.attendance}%</h2>
        <p>
          {data?.stats?.attendance >= 75
            ? 'You are above the 75% target. Keep attending consistently.'
            : 'You are below the 75% target. Prioritize upcoming classes and confirm records with faculty.'}
        </p>
      </div>

      <div
        className="attendance-ring"
        style={{ '--percent': (data?.stats?.attendance || 0) * 3.6 + 'deg' }}
      >
        <div>
          <b>{data?.stats?.attendance}%</b>
          <small>ATTENDED</small>
        </div>
      </div>
    </div>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>Subject-wise attendance report</h3>
          <p>Current recorded attendance by course</p>
        </div>
      </div>

      <div className="attendance-list">
        {metrics.map(m => (
          <div className="attendance-line" key={m.id}>
            <div className="attendance-course">
              <b>{m.course_name}</b>
              <small>{m.course_code}</small>
            </div>

            <div className="attendance-meter">
              <div className="mini-progress">
                <i className={m.attendance < 75 ? 'under' : ''} style={{ width: m.attendance + '%' }} />
              </div>
            </div>

            <b className={m.attendance < 75 ? 'text-red' : ''}>{m.attendance}%</b>

            <span className={'attendance-target ' + (m.attendance >= 75 ? 'good' : 'bad')}>
              {m.attendance >= 75 ? 'On target' : 'Below target'}
            </span>
          </div>
        ))}
      </div>
    </section>
  </>;
}

function Recommendations({ data }) {
  const metrics = data?.metrics || [];

  return <>
    <div className="section-intro">
      <div>
        <h2>Personalized recommendations</h2>
        <p>Actionable study suggestions generated from current academic indicators.</p>
      </div>
      <div className="spark-icon large"><Sparkles size={22} /></div>
    </div>

    <div className="recommendation-intro">
      <BrainCircuit size={22} />
      <div>
        <b>AI-assisted learning coach</b>
        <p>
          Recommendations are based on attendance, assignment scores, assessments,
          and engagement. They are intended to guide a conversation, not replace faculty judgment.
        </p>
      </div>
    </div>

    <div className="recommendation-grid">
      {metrics.map(m => (
        <article className="recommendation-card" key={m.id}>
          <div className="rec-head">
            <div className="course-icon"><BookOpen size={17} /></div>
            <RiskPill level={m.risk_level} />
          </div>

          <small>{m.course_code}</small>
          <h3>{m.course_name}</h3>
          <p>{m.recommendation}</p>

          <div className="reason-list">
            <b>Signals to review</b>
            {m.reasons.map((r, i) => (
              <span key={i}><CheckCircle2 size={14} />{r}</span>
            ))}
          </div>
        </article>
      ))}
    </div>
  </>;
}

function Timetable({ timetable }) {
  return <>
    <div className="section-intro">
      <div>
        <h2>Class timetable</h2>
        <p>Your published weekly class schedule.</p>
      </div>
      <div className="course-icon big"><CalendarDays size={22} /></div>
    </div>

    <div className="timetable-grid">
      {timetable.map(d => (
        <section className="panel day-panel" key={d.day}>
          <div className="day-title">
            <b>{d.day}</b>
            <span>{d.classes.length} classes</span>
          </div>

          {d.classes.map((c, i) => (
            <div className="class-block" key={i}>
              <div className="class-time">
                {c.start}
                <small>{c.end}</small>
              </div>
              <div className="class-info">
                <b>{c.name}</b>
                <small>{c.code}</small>
                <span>{c.room}</span>
              </div>
            </div>
          ))}
        </section>
      ))}

      {!timetable.length &&
        <div className="empty panel">No timetable has been published yet.</div>
      }
    </div>
  </>;
}

function AccountSettings({ user, role, onLogout }) {
  return <>
    <div className="section-intro">
      <div>
        <h2>Settings</h2>
        <p>Account details and session controls for your EduPulse workspace.</p>
      </div>
      <div className="course-icon big"><Settings size={22} /></div>
    </div>

    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>Account information</h3>
          <p>Your currently signed-in account</p>
        </div>
      </div>

      <div className="settings-account">
        <div className="avatar avatar-soft">{initials(user?.name || 'User')}</div>
        <div>
          <b>{user?.name || 'User'}</b>
          <p>{user?.email || 'No email available'}</p>
          <small>{role === 'teacher' ? 'Faculty / Teacher' : 'Student account'}</small>
        </div>
      </div>

      <div className="settings-actions">
        <button className="btn btn-primary" onClick={onLogout}>
          <LogOut size={16} /> Log out
        </button>
      </div>
    </section>
  </>;
}

function AddMetric({ students, token, close, done }) {
  const [form, setForm] = useState({
    student_id: students[0]?.id || '',
    course_code: 'EICSA 316',
    course_name: 'Data Structures',
    attendance: 75,
    assignment_avg: 70,
    assessment_avg: 65,
    engagement: 70
  });

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  function set(k, v) {
    setForm(p => ({ ...p, [k]: v }));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr('');

    try {
      await api('/metrics', token, {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          student_id: Number(form.student_id),
          attendance: Number(form.attendance),
          assignment_avg: Number(form.assignment_avg),
          assessment_avg: Number(form.assessment_avg),
          engagement: Number(form.engagement)
        })
      });

      done();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="eyebrow">FACULTY TOOLS</div>
            <h2>Add academic data</h2>
            <p>Saving a high-risk record can create an early-warning alert.</p>
          </div>
          <button className="icon-button" onClick={close}><X size={18} /></button>
        </div>

        <form onSubmit={submit} className="metric-form">
          <label>
            Student
            <select value={form.student_id} onChange={e => set('student_id', e.target.value)} required>
              {students.map(s => (
                <option value={s.id} key={s.id}>{s.name} · {s.student_code}</option>
              ))}
            </select>
          </label>

          <div className="form-two">
            <label>Course code
              <input value={form.course_code} onChange={e => set('course_code', e.target.value)} required />
            </label>
            <label>Course name
              <input value={form.course_name} onChange={e => set('course_name', e.target.value)} required />
            </label>
          </div>

          {[
            ['attendance', 'Attendance (%)'],
            ['assignment_avg', 'Assignment average (%)'],
            ['assessment_avg', 'Assessment average (%)'],
            ['engagement', 'Engagement (%)']
          ].map(([k, label]) => (
            <label key={k}>
              {label}
              <div className="range-input">
                <input type="range" min="0" max="100" value={form[k]} onChange={e => set(k, e.target.value)} />
                <b>{form[k]}%</b>
              </div>
            </label>
          ))}

          {err && <div className="login-error">{err}</div>}

          <button className="btn btn-primary login-submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save data & refresh AI signals'}
            <ChevronRight size={17} />
          </button>
        </form>
      </div>
    </div>
  );
}

function initials(name = '') {
  return name.split(' ').map(x => x[0]).slice(0, 2).join('').toUpperCase();
}

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

function avg(arr, key) {
  return arr.length
    ? Math.round(arr.reduce((a, x) => a + Number(x[key] || 0), 0) / arr.length)
    : 0;
}

createRoot(document.getElementById('root')).render(<App />);