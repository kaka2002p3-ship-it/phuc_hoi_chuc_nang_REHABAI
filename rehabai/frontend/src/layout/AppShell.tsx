import type { CSSProperties, ReactNode } from 'react';
import { Activity, BarChart3, Bell, Bot, Building2, Dumbbell, FlaskConical, History, Home, LogOut, Menu, Monitor, Moon, Settings, Sun, UserRound, X } from 'lucide-react';
import { NavLink, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth';
import { useTheme } from '../theme';
import { authHeaders } from '../api';
import { useUiHideSettings } from '../ui-hide-settings';

const allLinks = [
  ['/app', Home, 'Trang chủ'], ['/app/exercises', Dumbbell, 'Tập luyện'], ['/app/clinic', Building2, 'Phòng khám'],
  ['/app/history', History, 'Lịch sử'], ['/app/reports', BarChart3, 'Tiến trình'], ['/app/ai-coach', Bot, 'AI Coach'],
  ['/app/research', FlaskConical, 'Research Mode'], ['/app/profile', UserRound, 'Hồ sơ cá nhân'], ['/app/settings', Settings, 'Cài đặt'],
] as const;

const mobileLinks = [
  ['/app', Home, 'Trang chủ'], ['/app/exercises', Dumbbell, 'Bài tập'], ['/app/clinic', Building2, 'Phòng khám'],
  ['/app/reports', BarChart3, 'Tiến trình'], ['/app/ai-coach', Bot, 'AI Coach'], ['/app/profile', UserRound, 'Cá nhân'],
] as const;

function filterLinks(links: typeof allLinks, hidden: { research: boolean; clinic: boolean }) {
  return links.filter(([to]) => {
    if (hidden.clinic && to === '/app/clinic') return false;
    if (hidden.research && to === '/app/research') return false;
    return true;
  });
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, token, logout } = useAuth();
  const { mode, setMode } = useTheme();
  const uiHide = useUiHideSettings();
  const links = filterLinks(allLinks, { research: uiHide.hide_research_mode, clinic: uiHide.hide_clinic_link });
  const [open, setOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [remindersEnabled, setRemindersEnabled] = useState(true);
  const [recentSessions, setRecentSessions] = useState<{id:string;exercise:string;start_time:string;status:string}[]>([]);
  const [notifications, setNotifications] = useState<{id:string;type:string;title:string;body:string|null;is_read:boolean;created_at:string}[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const notificationRef = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  useEffect(() => {
    Promise.all([
      fetch('/api/settings', { headers: authHeaders(token) }).then(response => response.ok ? response.json() : null),
      fetch('/api/exercise/history', { headers: authHeaders(token) }).then(response => response.ok ? response.json() : []),
      fetch('/api/notifications', { headers: authHeaders(token) }).then(response => response.ok ? response.json() : null),
    ]).then(([settings, sessions, notificationsBox]) => {
      setRemindersEnabled(settings?.practice_reminders !== false);
      setRecentSessions(Array.isArray(sessions) ? sessions.slice(0, 3) : []);
      if (notificationsBox) {
        setNotifications(Array.isArray(notificationsBox.items) ? notificationsBox.items : []);
        setUnreadCount(typeof notificationsBox.unread === 'number' ? notificationsBox.unread : 0);
      }
    }).catch(() => setRecentSessions([]));
  }, [token, pathname]);
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) setNotificationsOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  const activeLinkIndex = links.findIndex(([to]) => {
    if (to === '/app') return pathname === '/app';
    if (to === '/app/exercises') return pathname.startsWith('/app/exercises') || pathname.startsWith('/app/practice/');
    return pathname === to || pathname.startsWith(`${to}/`);
  });
  const indicatorStyle = { '--nav-index': Math.max(activeLinkIndex, 0) } as CSSProperties;
  const themeSwitch = [
    { key: 'light', Icon: Sun, label: 'Giao diện sáng' },
    { key: 'system', Icon: Monitor, label: 'Theo hệ thống' },
    { key: 'dark', Icon: Moon, label: 'Giao diện tối' },
  ] as const;
  return <div className="app-shell">
    <button className="mobile-menu" onClick={()=>setOpen(v=>!v)} aria-label="Mở điều hướng">{open ? <X/> : <Menu/>}</button>
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <NavLink to="/app" className="sidebar-logo"><span><Activity /></span><div><strong>Rehab<span>AI</span></strong><small>Your Hand, Brighter Tomorrow</small></div></NavLink>
      <nav className="sidebar-nav" aria-label="Điều hướng chính"><i className={`sidebar-active-indicator ${activeLinkIndex < 0 ? 'is-hidden' : ''}`} style={indicatorStyle} aria-hidden="true"/>{links.map(([to, Icon, label], index)=><NavLink key={to} to={to} end={to==='/app'} className={index===activeLinkIndex?'active':undefined} onClick={()=>setOpen(false)}><Icon size={19}/><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-note"><span aria-hidden="true">✦</span><span>Mỗi chuyển động nhỏ đều đáng tự hào.</span></div>
      <div className="sidebar-user"><NavLink to="/app/profile" className="avatar avatar-link">{user?.avatar_data_url?<img src={user.avatar_data_url} alt=""/>:user?.full_name?.[0]?.toUpperCase() || 'R'}</NavLink><div><strong>{user?.full_name || 'Người tập'}</strong><small>{user?.email || 'Chế độ dùng thử'}</small></div><button onClick={logout} title="Đăng xuất" aria-label="Đăng xuất"><LogOut size={17}/></button></div>
    </aside>
    <main className="app-content">
      <header className="topbar">
        <div className="topbar-title"><span>REHABAI · WEB CARE</span><strong>Hành trình phục hồi của bạn</strong></div>
        <div className="mobile-topbar-brand" aria-label="RehabAI"><Activity size={20}/><strong>Rehab<span>AI</span></strong></div>
        <div className="topbar-actions">
          <div className="notification-center" ref={notificationRef}>
            <button className="icon-button" aria-label="Thông báo" aria-expanded={notificationsOpen} onClick={()=>setNotificationsOpen(value=>!value)}><Bell size={18}/>{(remindersEnabled || unreadCount>0) && <i className="notification-dot"/>}</button>
            {notificationsOpen&&<section className="notification-panel" aria-label="Danh sách thông báo">
              <header><div><strong>Thông báo</strong><small>Dữ liệu của tài khoản đang đăng nhập</small></div><NavLink to="/app/settings" onClick={()=>setNotificationsOpen(false)}>Cài đặt</NavLink></header>
              <div className="notification-list">
                {notifications.length>0&&<div style={{padding:'.4rem .2rem .1rem', fontSize:'.7rem', color:'var(--muted)'}}>{unreadCount} thông báo chưa đọc</div>}
                {notifications.map(notification=><NotificationItem key={notification.id} notification={notification} onDone={()=>setNotifications(prev=>prev.map(item=>item.id===notification.id?{...item,is_read:true}:item))}/>)}
                {remindersEnabled&&<NavLink to="/app/exercises" onClick={()=>setNotificationsOpen(false)} className="notification-item is-reminder"><Bell size={16}/><div><strong>Đến giờ vận động nhẹ</strong><span>Chọn một bài phù hợp và dừng nếu đau tăng.</span></div></NavLink>}
                {recentSessions.map(session=><NavLink key={session.id} to={`/app/history/${session.id}`} onClick={()=>setNotificationsOpen(false)} className="notification-item"><CheckNotification status={session.status}/><div><strong>{session.exercise}</strong><span>{new Date(session.start_time).toLocaleString('vi-VN')} · {session.status==='COMPLETED'?'Đã hoàn thành':'Chưa hoàn thành'}</span></div></NavLink>)}
                {!remindersEnabled&&notifications.length===0&&recentSessions.length===0&&<p>Chưa có thông báo mới.</p>}
              </div>
            </section>}
          </div>
          <div className="theme-switch" aria-label="Chọn giao diện">
            {themeSwitch.map(({key, Icon, label}) => <button key={key} className={mode===key?'active':''} onClick={()=>setMode(key)} aria-label={label}><Icon size={15}/></button>)}
          </div>
          <NavLink to="/app/profile" className="topbar-user"><span className="avatar">{user?.avatar_data_url?<img src={user.avatar_data_url} alt=""/>:user?.full_name?.[0]?.toUpperCase() || 'R'}</span><span><strong>{user?.full_name || 'Người tập'}</strong><small>Cùng cố gắng hôm nay</small></span></NavLink>
        </div>
      </header>
      {children}
    </main>
    <nav className="mobile-bottom-nav" aria-label="Điều hướng nhanh trên điện thoại">
      {mobileLinks.map(([to, Icon, label])=><NavLink key={to} to={to} end={to==='/app'}><Icon size={20}/><span>{label}</span></NavLink>)}
    </nav>
  </div>;
}

function CheckNotification({status}:{status:string}) {
  return <Activity size={16} aria-label={status==='COMPLETED'?'Hoàn thành':'Chưa hoàn thành'}/>;
}

function NotificationItem({ notification, onDone }: { notification: { id: string; type: string; title: string; body: string | null; is_read: boolean; created_at: string }, onDone: () => void }) {
  const { token } = useAuth();
  const markRead = async () => {
    if (notification.is_read) return;
    onDone();
    try { await fetch(`/api/notifications/${notification.id}/read`, { method: 'POST', headers: authHeaders(token) }); } catch { /* offline-tolerant */ }
  };
  return <button type="button" className={`notification-item ${notification.is_read ? '' : 'is-reminder'}`} onClick={markRead} style={{ textAlign: 'left', width: '100%', background: 'transparent', border: 'none', cursor: 'pointer' }}>
    <Bell size={16}/>
    <div><strong>{notification.title}</strong>{notification.body ? <span>{notification.body}</span> : null}<br/>
      <small style={{ color: 'var(--muted)' }}>{new Date(notification.created_at).toLocaleString('vi-VN')}{notification.is_read ? '' : ' · chưa đọc'}</small>
    </div>
  </button>;
}
