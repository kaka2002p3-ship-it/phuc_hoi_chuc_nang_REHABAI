import { useEffect, useState } from 'react';
import { Bell, Bot, Camera, CheckCircle2, EyeOff, Languages, Moon, RefreshCw, Save, ShieldAlert, WifiOff } from 'lucide-react';
import { PageTitle } from './Reports';
import { useAuth } from '../auth';
import { authHeaders } from '../api';
import { useTheme } from '../theme';
import type { ThemeMode } from '../theme';
import { useUiHideSettings, saveUiHideSettings, type UiHideSettings } from '../ui-hide-settings';

type Settings={language:string;pain_alerts:boolean;practice_reminders:boolean;theme:ThemeMode;camera_resolution:string};
type AssistantStatus={assistant_status:string;provider:string;model_tag:string};
const defaults:Settings={language:'vi',pain_alerts:true,practice_reminders:true,theme:'system',camera_resolution:'1280x720'};

export default function SettingsPage(){
 const {token}=useAuth(); const {mode,setMode}=useTheme(); const [value,setValue]=useState<Settings>(()=>({...defaults,theme:mode})); const [saved,setSaved]=useState(false); const [error,setError]=useState(''); const [assistant,setAssistant]=useState<AssistantStatus|null>(null); const [checkingAssistant,setCheckingAssistant]=useState(true);
 const uiHide = useUiHideSettings();
 const setHideToggle = (key: keyof UiHideSettings, next: boolean) => { saveUiHideSettings({ [key]: next }); };
 useEffect(()=>{fetch('/api/settings',{headers:authHeaders(token)}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{setValue(current=>({...defaults,...data,theme:current.theme}))}).catch(()=>setError('Không thể tải cài đặt từ máy chủ.'))},[token]);
 const checkAssistant=()=>{setCheckingAssistant(true);fetch('/api/chat/status',{headers:authHeaders(token)}).then(r=>r.ok?r.json():Promise.reject()).then(setAssistant).catch(()=>setAssistant({assistant_status:'MODEL_UNAVAILABLE',provider:'ollama-local',model_tag:'Không xác định'})).finally(()=>setCheckingAssistant(false))};
 useEffect(()=>{let active=true;fetch('/api/chat/status',{headers:authHeaders(token)}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{if(active)setAssistant(data)}).catch(()=>{if(active)setAssistant({assistant_status:'MODEL_UNAVAILABLE',provider:'ollama-local',model_tag:'Không xác định'})}).finally(()=>{if(active)setCheckingAssistant(false)});return()=>{active=false}},[token]);
 const update=(key:keyof Settings,next:string|boolean)=>{setValue(v=>({...v,[key]:next}));if(key==='theme')setMode(next as ThemeMode)};
 const save=async()=>{setError('');const r=await fetch('/api/settings',{method:'PUT',headers:authHeaders(token,true),body:JSON.stringify({...value,theme:mode})});if(!r.ok){setError('Không thể lưu cài đặt. Hãy thử lại.');return}setSaved(true);setTimeout(()=>setSaved(false),2500)};
 return <div><PageTitle title="Cài đặt" subtitle="Điều chỉnh trải nghiệm, camera và các nhắc nhở an toàn."/>{error&&<p className="form-error" role="alert">{error}</p>}<div className="settings-grid">
  <section className="surface settings-card"><h3><Languages/> Ngôn ngữ</h3><div className="segmented"><button className={value.language==='vi'?'active':''} onClick={()=>update('language','vi')}>Tiếng Việt</button><button className={value.language==='en'?'active':''} onClick={()=>update('language','en')}>English</button></div></section>
  <section className="surface settings-card"><h3><Bell/> Thông báo</h3><Toggle label="Nhắc nhở tập luyện" checked={value.practice_reminders} onChange={x=>update('practice_reminders',x)}/><Toggle label="Cảnh báo đau" checked={value.pain_alerts} onChange={x=>update('pain_alerts',x)}/></section>
  <section className="surface settings-card"><h3><Camera/> Thiết bị</h3><label>Độ phân giải<select value={value.camera_resolution} onChange={e=>update('camera_resolution',e.target.value)}><option>640x480</option><option>1280x720</option><option>1920x1080</option></select></label></section>
  <section className="surface settings-card"><h3><Moon/> Giao diện</h3><div className="segmented"><button className={mode==='light'?'active':''} onClick={()=>update('theme','light')}>Sáng</button><button className={mode==='system'?'active':''} onClick={()=>update('theme','system')}>Hệ thống</button><button className={mode==='dark'?'active':''} onClick={()=>update('theme','dark')}>Tối</button></div><div className="safety-mini"><ShieldAlert/> Chế độ cảnh báo y tế luôn được duy trì.</div><div className="safety-note"><strong>Lưu ý khi dùng AI Coach</strong><span>RehabAI chỉ hỗ trợ theo dõi và giải thích thông tin; không thay thế tư vấn, chẩn đoán hoặc điều trị y tế.</span></div></section>
  <section className="surface settings-card"><h3><EyeOff/>Ẩn trong giao diện</h3>
    <p style={{ color: 'var(--muted)', fontSize: '.8rem', margin: '0 0 .6rem' }}>Tắt hiển thị các mục dưới đây trên giao diện; người dùng có thể vào Cài đặt để bật lại. Không xóa dữ liệu hay chức năng phía sau.</p>
    <Toggle label="Research Mode (ẩn khỏi menu)" checked={uiHide.hide_research_mode} onChange={x=>setHideToggle('hide_research_mode', x)}/>
    <Toggle label="Cảnh báo quan trọng (ẩn trên trang chủ / tập luyện)" checked={uiHide.hide_clinical_warning} onChange={x=>setHideToggle('hide_clinical_warning', x)}/>
    <Toggle label="Phòng khám (ẩn khỏi menu bên)" checked={uiHide.hide_clinic_link} onChange={x=>setHideToggle('hide_clinic_link', x)}/>
  </section>
  <section className="surface settings-card assistant-settings"><h3><Bot/> AI Coach · Ollama</h3><div className={`assistant-health ${assistant?.assistant_status==='ready'?'ready':'unavailable'}`}>{assistant?.assistant_status==='ready'?<CheckCircle2/>:<WifiOff/>}<div><strong>{checkingAssistant?'Đang kiểm tra…':assistant?.assistant_status==='ready'?'Ollama local sẵn sàng':'Ollama không khả dụng'}</strong><span>Model: {assistant?.model_tag||'Đang xác định'} · {assistant?.provider||'ollama-local'}</span></div></div><button className="btn btn-secondary assistant-refresh" type="button" disabled={checkingAssistant} onClick={checkAssistant}><RefreshCw size={16}/>{checkingAssistant?'Đang kiểm tra':'Kiểm tra lại kết nối'}</button></section>
 </div><button className="btn btn-primary save-settings" onClick={save}><Save size={18}/>{saved?'Đã lưu':'Lưu cài đặt'}</button></div>
}
function Toggle({label,checked,onChange}:{label:string;checked:boolean;onChange:(x:boolean)=>void}){return <label className="toggle-row"><span>{label}</span><button type="button" className={`switch ${checked?'on':''}`} aria-pressed={checked} onClick={()=>onChange(!checked)}><i/></button></label>}
