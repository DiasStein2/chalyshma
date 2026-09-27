import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownRight, ArrowUpRight, BookOpen, CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, ClipboardCheck, GraduationCap, LayoutDashboard, LogOut, Menu, MoreHorizontal, Plus, Search, Settings2, Shield, Sparkles, Users, X } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
type User = { id: number; username: string; full_name: string; role: 'GLOBAL_ADMIN' | 'OLYMPIAD_LEAD'; active?: boolean }
type Olympiad = { id: number; name: string; description?: string; lead_user_id?: number; lead?: User }
type Student = { id: number; full_name: string; class_name: string; olympiad_id: number; active: boolean }
type Event = { id: number; title: string; date: string; end_date?: string | null }
type Row = { student: Student; attendance: { status: 'PRESENT'|'ABSENT' } | null }
type StudentAttendance = { id: number; date: string; status: 'PRESENT'|'ABSENT'; marked_by_user_id: number }

async function request(path: string, token: string, init: RequestInit = {}) {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...init.headers } })
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || 'Something went wrong') }
  if (response.status === 204) return null
  return response.json()
}
const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
const prettyDate = (date: string) => new Date(`${date}T12:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [user, setUser] = useState<User | null>(null)
  const [page, setPage] = useState('Dashboard')
  const [mobileNav, setMobileNav] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [olympiads, setOlympiads] = useState<Olympiad[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [overview, setOverview] = useState<any>(null)
  const [attendance, setAttendance] = useState<Row[]>([])
  const [attDate, setAttDate] = useState(todayISO())
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState('')
  const [busy, setBusy] = useState(false)
  const [selectedMonth, setSelectedMonth] = useState(new Date())
  const [historyStudent, setHistoryStudent] = useState<Student | null>(null)
  const [historyRows, setHistoryRows] = useState<StudentAttendance[]>([])
  const [historyStats, setHistoryStats] = useState<any>(null)
  const [historyLoading, setHistoryLoading] = useState(false)

  const admin = user?.role === 'GLOBAL_ADMIN'
  const nav = useMemo(() => [
    { title: 'WORKSPACE', items: [{ name: 'Dashboard', icon: LayoutDashboard }, { name: 'Attendance', icon: ClipboardCheck }, { name: 'Students', icon: GraduationCap }, ...(admin ? [{ name: 'Olympiads', icon: BookOpen }] : []), { name: 'Statistics', icon: Activity }, { name: 'Calendar', icon: CalendarDays }] },
    ...(admin ? [{ title: 'ADMINISTRATION', items: [{ name: 'Users', icon: Users }] }] : []),
  ], [admin])

  async function loadData(t = token) {
    try {
      const me = await request('/auth/me', t) as User; setUser(me)
      const [o, s, ov, ev, accountList] = await Promise.all([request('/olympiads', t), request('/students?active=true', t), request('/statistics/overview', t), request('/calendar/events', t), me.role === 'GLOBAL_ADMIN' ? request('/users', t) : Promise.resolve([])])
      setOlympiads(o); setStudents(s); setOverview(ov); setEvents(ev); setUsers(accountList)
    } catch (e: any) { logout(); setError(e.message) }
  }
  useEffect(() => { if (token) loadData(token) }, [token])
  useEffect(() => { if (token && user) loadAttendance() }, [token, user, attDate])
  async function loadAttendance() { try { const data = await request(`/attendance/date/${attDate}`, token); setAttendance(data) } catch (e: any) { setError(e.message) } }
  async function openStudentForm() {
    try {
      const latestOlympiads = await request('/olympiads', token) as Olympiad[]
      setOlympiads(latestOlympiads)
      if (!latestOlympiads.length) { setError('No olympiad directions are available for your account yet.'); return }
      setError('')
      setModal('student')
    } catch (e: any) { setError(e.message) }
  }
  async function openStudentHistory(student: Student) {
    setHistoryStudent(student); setHistoryRows([]); setHistoryStats(null); setHistoryLoading(true)
    try {
      const [records, stats] = await Promise.all([
        request(`/students/${student.id}/attendance`, token),
        request(`/statistics/students/${student.id}`, token),
      ])
      setHistoryRows(records); setHistoryStats(stats)
    } catch (e: any) { setError(e.message); setHistoryStudent(null) }
    finally { setHistoryLoading(false) }
  }
  function logout() { localStorage.removeItem('token'); setToken(''); setUser(null) }
  function notify(msg: string) { setToast(msg); window.setTimeout(() => setToast(''), 2800) }

  if (!token || !user) return <Login onLogin={async (username, password) => { setError(''); try { const data: any = await request('/auth/login', '', { method: 'POST', body: JSON.stringify({ username, password }), headers: {} }); localStorage.setItem('token', data.access_token); setToken(data.access_token); setUser(data.user) } catch (e: any) { setError(e.message) } }} error={error} />

  async function saveAttendance() {
    setBusy(true)
    try { await request('/attendance', token, { method: 'POST', body: JSON.stringify({ date: attDate, entries: attendance.map(row => ({ student_id: row.student.id, status: row.attendance?.status || 'ABSENT' })) }) }); notify('Attendance saved'); loadData() }
    catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }
  function markAll(status: 'PRESENT'|'ABSENT') { setAttendance(rows => rows.map(row => ({ ...row, attendance: { status } }))) }
  function setStatus(id: number, status: 'PRESENT'|'ABSENT') { setAttendance(rows => rows.map(row => row.student.id === id ? { ...row, attendance: { status } } : row)) }
  const presentCount = attendance.filter(x => x.attendance?.status === 'PRESENT').length

  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); const fd = new FormData(e.currentTarget); const values = Object.fromEntries(fd.entries())
    try {
      let path = '', method = 'POST', body: any = values
      if (modal === 'student') { path = '/students'; body = { ...values, olympiad_id: Number(values.olympiad_id) } }
      if (modal === 'olympiad') { path = '/olympiads'; body = { ...values, lead_user_id: values.lead_user_id ? Number(values.lead_user_id) : null } }
      if (modal === 'event') { path = '/calendar/events'; body = { ...values, end_date: values.end_date || null } }
      if (modal === 'user') { path = '/users'; body = { ...values, role: 'OLYMPIAD_LEAD' } }
      await request(path, token, { method, body: JSON.stringify(body) }); setModal(''); notify('Saved successfully'); await loadData()
    } catch (e: any) { setError(e.message) }
  }

  const filteredStudents = students.filter(s => s.full_name.toLowerCase().includes(search.toLowerCase()))
  const attendanceView = <>
    <div className="page-heading attendance-heading"><div><div className="eyebrow">DAILY ROLL CALL</div><h1>Attendance</h1><p>Take attendance for your session in a few taps.</p></div><button className="primary" onClick={saveAttendance} disabled={busy || !attendance.length}><Check size={17}/>{busy ? 'Saving…' : 'Save attendance'}</button></div>
    <div className="attendance-banner"><div className="banner-icon"><ClipboardCheck size={22}/></div><div className="banner-main"><strong>{olympiads[0]?.name || 'Your olympiad'} session</strong><span>{presentCount} of {attendance.length} students marked present</span></div><label className="date-picker"><CalendarDays size={17}/><input type="date" value={attDate} onChange={e => setAttDate(e.target.value)}/></label></div>
    <div className="toolbar"><div><h2>Student list</h2><span className="muted">Choose present or absent for each student</span></div><button className="button-light" onClick={() => markAll('PRESENT')}><Check size={16}/> Mark all present</button></div>
    <div className="student-roll">{attendance.map((row, i) => <div className="roll-row" key={row.student.id}><div className="roll-number">{String(i+1).padStart(2,'0')}</div><div className="avatar">{row.student.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</div><div className="roll-name"><strong>{row.student.full_name}</strong><span>{row.student.class_name} · {olympiads.find(o=>o.id===row.student.olympiad_id)?.name}</span><button className="roll-history" onClick={()=>openStudentHistory(row.student)}>View attendance history</button></div><div className="attendance-toggle"><button className={row.attendance?.status === 'PRESENT' ? 'selected present' : ''} onClick={()=>setStatus(row.student.id,'PRESENT')}><Check size={15}/> Present</button><button className={row.attendance?.status === 'ABSENT' ? 'selected absent' : ''} onClick={()=>setStatus(row.student.id,'ABSENT')}><X size={15}/> Absent</button></div></div>)}{!attendance.length&&<Empty title="No active students" text="Add students to an olympiad direction to take attendance."/>}</div>
    <div className="bottom-save"><span><span className="online-dot"/> Changes save when you tap the button</span><button className="primary" onClick={saveAttendance} disabled={busy || !attendance.length}><Check size={17}/> Save attendance</button></div>
  </>

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'show' : ''}`}><div className="brand"><div className="brand-mark"><Sparkles size={18}/></div><div><b>olympia</b><span>STUDENT SUCCESS</span></div><button className="close-mobile" onClick={()=>setMobileNav(false)}><X/></button></div><div className="workspace-label">YOUR WORKSPACE</div>{nav.map(group=><div className="nav-group" key={group.title}><div className="nav-caption">{group.title}</div>{group.items.map(item=><button key={item.name} className={`nav-item ${page===item.name?'active':''}`} onClick={()=>{setPage(item.name);setMobileNav(false);loadData()}}><item.icon size={18}/><span>{item.name}</span>{item.name==='Attendance' && <i className="nav-pip"/>}</button>)}</div>)}<div className="sidebar-bottom"><div className="help-card"><CircleHelp size={18}/><div><strong>Need a hand?</strong><span>Visit the quick guide</span></div><ChevronRight size={15}/></div><button className="profile" onClick={logout}><div className="profile-avatar">{user.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</div><div className="profile-info"><b>{user.full_name}</b><span>{admin?'Global administrator':'Olympiad lead'}</span></div><LogOut size={17}/></button></div></aside>
    {mobileNav && <div className="scrim" onClick={()=>setMobileNav(false)}/>}
    <main className="main"><header className="topbar"><button className="mobile-menu" onClick={()=>setMobileNav(true)}><Menu/></button><div className="crumb">Olympia <ChevronRight size={14}/><strong>{page}</strong></div><div className="top-actions"><span className="date-chip"><CalendarDays size={15}/>{new Date().toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'})}</span><button className="icon-button"><CircleHelp size={18}/></button><div className="top-avatar">{user.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</div></div></header>
      <div className="content">
        {error && <div className="error-banner"><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}
        {page === 'Attendance' ? attendanceView : page === 'Dashboard' ? <Dashboard user={user} overview={overview} olympiads={olympiads} setPage={setPage}/>
          : page === 'Students' ? <><PageHeading title="Students" subtitle="A clear view of the students in your olympiad groups." action={<button className="primary" onClick={openStudentForm}><Plus size={17}/> Add student</button>}/><div className="toolbar card-toolbar"><div><h2>All students <span className="count-badge">{filteredStudents.length}</span></h2><span className="muted">Active students across your directions</span></div><div className="searchbox"><Search size={17}/><input placeholder="Search students..." value={search} onChange={e=>setSearch(e.target.value)}/></div></div><div className="table-card"><table><thead><tr><th>STUDENT</th><th>CLASS</th><th>OLYMPIAD</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{filteredStudents.map(s=><tr key={s.id}><td><div className="table-person"><div className="avatar">{s.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</div><strong>{s.full_name}</strong></div></td><td>{s.class_name}</td><td><span className="subject-pill">{olympiads.find(o=>o.id===s.olympiad_id)?.name}</span></td><td><span className="status"><i/> Active</span></td><td><div className="student-actions"><button className="history-button" onClick={()=>openStudentHistory(s)}><ClipboardCheck size={14}/> Attendance</button><button className="deactivate" onClick={async()=>{if(!confirm(`Deactivate ${s.full_name}? Attendance history will be kept.`))return;try{await request(`/students/${s.id}`,token,{method:'DELETE'});notify('Student deactivated');loadData()}catch(e:any){setError(e.message)}}}>Deactivate</button></div></td></tr>)}</tbody></table>{!filteredStudents.length&&<Empty title="No students found" text="Try another search or add your first student."/>}</div></>
          : page === 'Olympiads' ? <><PageHeading title="Olympiad directions" subtitle="Manage study groups, descriptions, and responsible leads." action={<button className="primary" onClick={()=>setModal('olympiad')}><Plus size={17}/> New direction</button>}/><div className="direction-grid">{olympiads.map(o=><div className="direction-card" key={o.id}><div className="direction-top"><div className="subject-icon"><BookOpen size={19}/></div></div><h3>{o.name}</h3><p>{o.description || 'No description provided'}</p><div className="direction-footer"><div className="profile-avatar small">{o.lead?.full_name?.split(' ').map(p=>p[0]).slice(0,2).join('') || '—'}</div><div><span>OLYMPIAD LEAD</span><strong>{o.lead?.full_name || 'Unassigned'}</strong></div><b className="group-count">{students.filter(s=>s.olympiad_id===o.id).length} students</b></div></div>)}{!olympiads.length&&<Empty title="No olympiad directions yet" text="Create a direction, then assign its lead and add students."/>}</div></>
          : page === 'Statistics' ? <Statistics token={token} olympiads={olympiads}/>
          : page === 'Calendar' ? <CalendarView events={events} month={selectedMonth} setMonth={setSelectedMonth} canEdit={!!admin} onAdd={()=>setModal('event')} />
          : page === 'Users' ? <UsersPage token={token} users={users} onAdd={()=>setModal('user')} onChanged={loadData}/>
          : <Dashboard user={user} overview={overview} olympiads={olympiads} setPage={setPage}/>}
      </div>
    </main>
    {modal && <Modal title={modal==='student'?'Add a student':modal==='olympiad'?'Create a direction':modal==='event'?'Add calendar event':'Create a user'} onClose={()=>setModal('')}><form onSubmit={submitForm}>{modal==='student'&&<><Field label="Full name" name="full_name" placeholder="Student full name"/><Field label="Class" name="class_name" placeholder="e.g. 10B"/><label className="form-field"><span>Olympiad direction</span><select name="olympiad_id" required>{olympiads.map(o=><option value={o.id} key={o.id}>{o.name}</option>)}</select></label></>}{modal==='olympiad'&&<><Field label="Direction name" name="name" placeholder="Olympiad direction name"/><Field label="Description" name="description" placeholder="Optional description" required={false}/><label className="form-field"><span>Olympiad lead</span><select name="lead_user_id"><option value="">Unassigned</option>{users.filter(u=>u.role==='OLYMPIAD_LEAD'&&u.active!==false).map(u=><option key={u.id} value={u.id}>{u.full_name} (@{u.username})</option>)}</select></label></>}{modal==='event'&&<><Field label="Event title" name="title" placeholder="Olympiad event title"/><Field label="Start date" name="date" type="date"/><Field label="End date" name="end_date" type="date" required={false}/></>}{modal==='user'&&<><Field label="Full name" name="full_name" placeholder="Full name"/><Field label="Username" name="username" placeholder="Username"/><Field label="Temporary password" name="password" type="password" placeholder="At least 8 characters"/></>}<div className="modal-actions"><button type="button" className="button-light" onClick={()=>setModal('')}>Cancel</button><button type="submit" className="primary">Save changes</button></div></form></Modal>}
    {historyStudent && <Modal title="Student attendance" onClose={()=>setHistoryStudent(null)}><div className="history-student-head"><div className="avatar">{historyStudent.full_name.split(' ').map(p=>p[0]).slice(0,2).join('')}</div><div><strong>{historyStudent.full_name}</strong><span>{historyStudent.class_name} · {olympiads.find(o=>o.id===historyStudent.olympiad_id)?.name}</span></div></div>{historyLoading ? <div className="history-loading">Loading attendance…</div> : <><div className="history-stats"><div><span>SESSIONS</span><strong>{historyStats?.sessions ?? 0}</strong></div><div><span>PRESENT</span><strong className="present-value">{historyStats?.present ?? 0}</strong></div><div><span>ABSENT</span><strong className="absent-value">{historyStats?.absent ?? 0}</strong></div><div><span>ATTENDANCE</span><strong>{historyStats?.percentage ?? 0}%</strong></div></div><div className="history-list-heading"><strong>Attendance history</strong><span>{historyRows.length} records</span></div><div className="history-list">{historyRows.map(record=><div className="history-row" key={record.id}><CalendarDays size={16}/><span>{prettyDate(record.date)}</span><b className={record.status==='PRESENT'?'history-present':'history-absent'}>{record.status==='PRESENT'?'Present':'Absent'}</b></div>)}{!historyRows.length&&<Empty title="No attendance recorded" text="Attendance records will appear here after sessions are saved."/>}</div></>}</Modal>}
    {toast&&<div className="toast"><Check size={17}/>{toast}</div>}
  </div>
}

function Login({ onLogin, error }: {onLogin:(u:string,p:string)=>void;error:string}) { const [u,setU]=useState('');const [p,setP]=useState('');return <div className="login-wrap"><div className="login-brand"><div className="brand-mark"><Sparkles size={19}/></div><div><b>olympia</b><span>STUDENT SUCCESS</span></div></div><div className="login-card"><div className="eyebrow">WELCOME BACK</div><h1>Sign in to your workspace</h1><p>Keep every session, student, and achievement in one place.</p>{error&&<div className="error-banner">{error}</div>}<form onSubmit={e=>{e.preventDefault();onLogin(u,p)}}><Field label="Username" name="login-user" placeholder="Your username" value={u} onChange={setU}/><Field label="Password" name="login-password" type="password" placeholder="Your password" value={p} onChange={setP}/><button className="primary login-submit">Continue <ChevronRight size={17}/></button></form><div className="login-foot"><Shield size={15}/> Secure access for your olympiad community</div></div><span className="login-version">OLYMPIAD MANAGEMENT PLATFORM · 2026</span></div> }
function Field(p:any){return <label className="form-field"><span>{p.label}</span><input name={p.name} type={p.type||'text'} placeholder={p.placeholder} required={p.required!==false} value={p.value} onChange={p.onChange ? (event)=>p.onChange(event.target.value) : undefined}/></label>}
function PageHeading({title,subtitle,action}:any){return <div className="page-heading"><div><div className="eyebrow">PROGRAM MANAGEMENT</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>}
function Dashboard({user,overview,olympiads,setPage}:any){return <><div className="welcome-line"><div><div className="eyebrow">{new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'}).toUpperCase()}</div><h1>Good morning, {user.full_name.split(' ')[0]} <span>✦</span></h1><p>Here’s what’s happening across your olympiad program today.</p></div><button className="button-light" onClick={()=>setPage('Calendar')}><CalendarDays size={17}/> View calendar</button></div><div className="metric-grid"><Metric title="Directions" value={overview?.directions ?? '—'} detail="Active olympiad groups" icon={<BookOpen/>} tone="purple" trend="Across your program"/><Metric title="Active students" value={overview?.total_students ?? '—'} detail="Currently enrolled" icon={<GraduationCap/>} tone="blue" trend="Learning every day"/><Metric title="Present today" value={overview?.today_present ?? '—'} detail="Checked in so far" icon={<Check/>} tone="green" trend="Attendance marked"/><Metric title="Absent today" value={overview?.today_absent ?? '—'} detail="Across all groups" icon={<ArrowDownRight/>} tone="amber" trend="Today’s sessions"/></div><div className="dashboard-grid"><div className="panel overview-panel"><div className="panel-head"><div><h2>Group overview</h2><span>Attendance performance by direction</span></div><button className="text-action" onClick={()=>setPage('Statistics')}>View stats <ChevronRight size={15}/></button></div>{(overview?.olympiads||[]).map((o:any)=>{const group=olympiads.find((x:any)=>x.id===o.olympiad_id);return <div className="overview-row" key={o.olympiad_id}><div className="subject-icon"><BookOpen size={18}/></div><div className="overview-name"><strong>{group?.name||'Olympiad'}</strong><span>{o.total_students} students · {o.sessions_recorded} sessions logged</span></div><div className="progress"><i style={{width:`${o.average_attendance_percentage}%`}}/></div><b className="percent">{o.average_attendance_percentage}%</b></div>})}{!overview?.olympiads?.length&&<Empty title="Your workspace is ready" text="Add students and take attendance to see your group overview."/>}</div><div className="panel events-panel"><div className="panel-head"><div><h2>Upcoming events</h2><span>Across the olympiad calendar</span></div><button className="icon-button" onClick={()=>setPage('Calendar')}><ChevronRight size={18}/></button></div>{(overview?.upcoming_events||[]).slice(0,4).map((e:any)=><div className="event-row" key={e.id}><div className="event-date"><b>{new Date(`${e.date}T12:00:00`).getDate()}</b><span>{new Date(`${e.date}T12:00:00`).toLocaleDateString('en-US',{month:'short'}).toUpperCase()}</span></div><div><strong>{e.title}</strong><span>{prettyDate(e.date)}</span></div></div>)}{!overview?.upcoming_events?.length&&<Empty title="No upcoming events" text="Add calendar events to see them here."/>}<button className="calendar-link" onClick={()=>setPage('Calendar')}>Open full calendar <ChevronRight size={15}/></button></div></div></>}
function Metric({title,value,detail,icon,tone,trend}:any){return <div className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><div className="metric-trend"><ArrowUpRight size={14}/>{trend}</div><span className="metric-title">{title}</span><strong className="metric-value">{value}</strong><span className="metric-detail">{detail}</span></div>}
function Empty({title,text}:any){return <div className="empty"><div className="empty-icon"><Sparkles size={20}/></div><strong>{title}</strong><span>{text}</span></div>}
function Modal({title,onClose,children}:any){return <div className="modal-backdrop" onClick={onClose}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modal-header"><h2>{title}</h2><button className="icon-button" onClick={onClose}><X size={19}/></button></div>{children}</div></div>}
function Statistics({token,olympiads}:any){
  const [data,setData]=useState<any[]>([]),[range,setRange]=useState('month'),[start,setStart]=useState(todayISO()),[end,setEnd]=useState(todayISO())
  useEffect(()=>{
    let from: string|undefined, to: string|undefined
    const now=new Date()
    if(range==='today') from=to=todayISO()
    if(range==='week'){const monday=new Date(now);monday.setDate(now.getDate()-((now.getDay()+6)%7));from=`${monday.getFullYear()}-${String(monday.getMonth()+1).padStart(2,'0')}-${String(monday.getDate()).padStart(2,'0')}`;to=todayISO()}
    if(range==='month') from=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-01`,to=todayISO()
    if(range==='custom') from=start,to=end
    const suffix=from?`?start=${from}&end=${to}`:''
    Promise.all(olympiads.map((o:any)=>request(`/statistics/olympiads/${o.id}${suffix}`,token))).then(setData).catch(()=>{})
  },[token,olympiads,range,start,end])
  return <><PageHeading title="Attendance statistics" subtitle="Understand participation across your olympiad groups." action={<div className="range-controls"><select className="select-filter" value={range} onChange={e=>setRange(e.target.value)}><option value="today">Today</option><option value="week">This week</option><option value="month">This month</option><option value="all">All time</option><option value="custom">Custom range</option></select>{range==='custom'&&<><input className="date-filter" type="date" value={start} onChange={e=>setStart(e.target.value)}/><input className="date-filter" type="date" value={end} onChange={e=>setEnd(e.target.value)}/></>}</div>}/><div className="stats-cards">{data.map((d:any,i:number)=><div className="metric-card" key={d.olympiad_id}><div className="metric-icon blue"><Activity/></div><span className="metric-title">{olympiads[i]?.name}</span><strong className="metric-value">{d.average_attendance_percentage}%</strong><span className="metric-detail">Average attendance · {d.total_students} students</span><div className="stat-bars">{d.top_attenders?.slice(0,5).map((s:any)=><div key={s.student_id} title={`${s.full_name}: ${s.percentage}%`} style={{height:`${Math.max(s.percentage,4)}%`}}/>)}</div></div>)}</div><div className="table-card stats-table"><div className="table-title"><h2>Student performance</h2><span className="muted">Attendance for the selected period</span></div><table><thead><tr><th>STUDENT</th><th>DIRECTION</th><th>PRESENT</th><th>ABSENT</th><th>ATTENDANCE</th></tr></thead><tbody>{data.flatMap((d:any,i:number)=>d.students?.map((s:any)=><tr key={s.student_id}><td><strong>{s.full_name}</strong></td><td>{olympiads[i]?.name}</td><td>{s.present}</td><td>{s.absent}</td><td><span className="status"><i/> {s.percentage}%</span></td></tr>))}</tbody></table></div></>}
function CalendarView({events,month,setMonth,canEdit,onAdd}:any){
  const year=month.getFullYear(),m=month.getMonth(),first=new Date(year,m,1),offset=(first.getDay()+6)%7,days=new Date(year,m+1,0).getDate()
  const cells=[...Array(offset).fill(null),...Array.from({length:days},(_,i)=>i+1)]
  while(cells.length%7)cells.push(null)
  const weeks=Array.from({length:cells.length/7},(_,i)=>cells.slice(i*7,i*7+7))
  const monthStart=new Date(year,m,1),monthEnd=new Date(year,m,days)
  const activeEvents=events.filter((e:Event)=>{const start=new Date(`${e.date}T12:00:00`),end=new Date(`${e.end_date||e.date}T12:00:00`);return start<=monthEnd&&end>=monthStart})
  const rangeLabel=(e:Event)=>e.end_date&&e.end_date!==e.date?`${prettyDate(e.date)} – ${prettyDate(e.end_date)}`:prettyDate(e.date)
  return <><PageHeading title="Calendar" subtitle="Your year of olympiad milestones, all in one place." action={canEdit&&<button className="primary" onClick={onAdd}><Plus size={17}/> Add event</button>}/><div className="calendar-layout"><div className="panel calendar-panel"><div className="calendar-top"><div><h2>{month.toLocaleDateString('en-US',{month:'long',year:'numeric'})}</h2><span>Olympiad events and key dates</span></div><div className="month-controls"><button className="icon-button" onClick={()=>setMonth(new Date(year,m-1,1))}><ChevronLeft/></button><button className="icon-button" onClick={()=>setMonth(new Date())}>Today</button><button className="icon-button" onClick={()=>setMonth(new Date(year,m+1,1))}><ChevronRight/></button></div></div><div className="calendar-grid"><div className="calendar-weekdays">{['MON','TUE','WED','THU','FRI','SAT','SUN'].map(d=><span className="weekday" key={d}>{d}</span>)}</div>{weeks.map((week,weekIndex)=>{
    const weekStart=new Date(year,m,1-offset+weekIndex*7),weekEnd=new Date(year,m,7-offset+weekIndex*7)
    const segments=activeEvents.flatMap((event:Event)=>{const start=new Date(`${event.date}T12:00:00`),end=new Date(`${event.end_date||event.date}T12:00:00`);if(start>weekEnd||end<weekStart)return[];const from=Math.max(0,Math.floor((start.getTime()-weekStart.getTime())/86400000)),to=Math.min(6,Math.floor((end.getTime()-weekStart.getTime())/86400000));return[{event,from,to}]})
    return <div className="calendar-week" key={weekIndex} style={{minHeight:Math.max(76,58+segments.length*19)}}>{week.map((d,i)=><div className={`cal-cell ${d===new Date().getDate()&&m===new Date().getMonth()&&year===new Date().getFullYear()?'today':''}`} key={`${weekIndex}-${i}`}>{d&&<span className="cal-day">{d}</span>}</div>)}{segments.map(({event,from,to},lane)=><div className="cal-event cal-event-span" key={`${weekIndex}-${event.id}`} title={`${event.title}: ${rangeLabel(event)}`} style={{left:`${from/7*100}%`,width:`${(to-from+1)/7*100}%`,top:30+lane*19}}>{event.title}</div>)}</div>
  })}</div></div><div className="panel side-events"><div className="panel-head"><div><h2>This month</h2><span>{month.toLocaleDateString('en-US',{month:'long'})} schedule</span></div></div>{activeEvents.map((e:Event)=><div className="event-row" key={e.id}><div className="event-date"><b>{new Date(`${e.date}T12:00:00`).getDate()}</b><span>{new Date(`${e.date}T12:00:00`).toLocaleDateString('en-US',{month:'short'}).toUpperCase()}</span></div><div><strong>{e.title}</strong><span>{rangeLabel(e)}</span></div></div>)}{!activeEvents.length&&<Empty title="No events this month" text="Your calendar is clear."/>}</div></div></>}
function UsersPage({token,users,onAdd,onChanged}:any){return <><PageHeading title="Users & access" subtitle="Manage the people who keep your olympiad groups moving." action={<button className="primary" onClick={onAdd}><Plus size={17}/> Add user</button>}/><div className="table-card"><table><thead><tr><th>USER</th><th>USERNAME</th><th>ROLE</th><th>STATUS</th><th></th></tr></thead><tbody>{users.map((u:User)=><tr key={u.id}><td><div className="table-person"><div className="avatar">{u.full_name.split(' ').map(x=>x[0]).slice(0,2).join('')}</div><strong>{u.full_name}</strong></div></td><td>{u.username}</td><td><span className="subject-pill">{u.role==='GLOBAL_ADMIN'?'Global admin':'Olympiad lead'}</span></td><td><span className={u.active===false?'inactive-status':'status'}><i/> {u.active===false?'Inactive':'Active'}</span></td><td>{u.role==='OLYMPIAD_LEAD'&&u.active!==false&&<button className="deactivate" onClick={async()=>{if(!confirm(`Deactivate ${u.full_name}? Their historical attendance will remain.`))return;try{await request(`/users/${u.id}`,token,{method:'DELETE'});await onChanged()}catch(e:any){alert(e.message)}}}>Deactivate</button>}</td></tr>)}</tbody></table>{!users.length&&<Empty title="No users yet" text="Create an Olympiad Lead account to assign to a direction."/>}</div></>}
