import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Activity, BarChart3, Camera, ChevronRight, HeartPulse, History, ImagePlus, Medal, Pencil, Save, Settings, Target, UserRound, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { authHeaders } from '../api';
import { useAuth } from '../auth';
import type { User } from '../auth';
import heroCompanion from '../assets/illustrations/hero-companion-3d.png';

type Summary={total_sessions:number;completed_sessions:number;completion_rate:number};
type ProfileForm={full_name:string;phone:string;bio:string;avatar_data_url:string|null;weekly_goal:number;height_cm:string;weight_kg:string};

const emptySummary:Summary={total_sessions:0,completed_sessions:0,completion_rate:0};

function asForm(user:User):ProfileForm{return {full_name:user.full_name||'',phone:user.phone||'',bio:user.bio||'',avatar_data_url:user.avatar_data_url||null,weekly_goal:user.weekly_goal||3,height_cm:user.height_cm?.toString()||'',weight_kg:user.weight_kg?.toString()||''}}

async function optimizeAvatar(file:File):Promise<string>{
  if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.');
  if(file.size>8*1024*1024)throw new Error('Ảnh gốc không được vượt quá 8 MB.');
  const bitmap=await createImageBitmap(file); const side=Math.min(bitmap.width,bitmap.height); const sourceX=Math.max(0,(bitmap.width-side)/2); const sourceY=Math.max(0,(bitmap.height-side)/2); const size=Math.min(640,side);
  const canvas=document.createElement('canvas');canvas.width=Math.max(1,size);canvas.height=Math.max(1,size);
  const context=canvas.getContext('2d');if(!context)throw new Error('Trình duyệt không thể xử lý ảnh này.');context.drawImage(bitmap,sourceX,sourceY,side,side,0,0,size,size);bitmap.close();
  let quality=.86;let result=canvas.toDataURL('image/webp',quality);while(result.length>1_000_000&&quality>.45){quality-=.1;result=canvas.toDataURL('image/webp',quality)}
  if(result.length>1_100_000)throw new Error('Không thể tối ưu ảnh xuống dung lượng an toàn.');return result;
}

export default function Profile(){
 const {user,token,updateUser}=useAuth(); const [profile,setProfile]=useState<User|null>(user); const [form,setForm]=useState<ProfileForm>(asForm(user!)); const [summary,setSummary]=useState(emptySummary); const [editing,setEditing]=useState(false); const [saving,setSaving]=useState(false); const [error,setError]=useState(''); const fileRef=useRef<HTMLInputElement>(null);
 useEffect(()=>{const headers=authHeaders(token);Promise.all([fetch('/api/users/me',{headers}).then(r=>r.ok?r.json():Promise.reject()),fetch('/api/reports/summary',{headers}).then(r=>r.ok?r.json():emptySummary)]).then(([next,stats])=>{setProfile(next);setForm(asForm(next));setSummary(stats);updateUser(next)}).catch(()=>setError('Không thể tải hồ sơ từ máy chủ.'))},[token,updateUser]);
 if(!profile)return null;
 const chooseAvatar=async(event:ChangeEvent<HTMLInputElement>)=>{const file=event.target.files?.[0];if(!file)return;setError('');try{const avatar=await optimizeAvatar(file);setForm(value=>({...value,avatar_data_url:avatar}))}catch(reason){setError(reason instanceof Error?reason.message:'Không thể xử lý ảnh.')}finally{event.target.value=''}};
 const save=async(event:FormEvent)=>{event.preventDefault();setSaving(true);setError('');try{const response=await fetch('/api/users/me',{method:'PUT',headers:authHeaders(token,true),body:JSON.stringify({...form,phone:form.phone||null,bio:form.bio||null,height_cm:form.height_cm?Number(form.height_cm):null,weight_kg:form.weight_kg?Number(form.weight_kg):null})});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Không thể lưu hồ sơ.');setProfile(data);setForm(asForm(data));updateUser(data);setEditing(false)}catch(reason){setError(reason instanceof Error?reason.message:'Không thể lưu hồ sơ.')}finally{setSaving(false)}};
 const cards=[
  {icon:<UserRound/>,title:'Thông tin cá nhân',text:'Chỉnh sửa tên, ảnh đại diện, số điện thoại và giới thiệu.',action:()=>setEditing(true)},
  {icon:<Target/>,title:'Mục tiêu & kế hoạch',text:`Mục tiêu hiện tại: ${form.weekly_goal} buổi mỗi tuần.`,action:()=>setEditing(true)},
  {icon:<BarChart3/>,title:'Tiến trình của tôi',text:`${summary.completed_sessions} buổi đã hoàn thành từ dữ liệu ghi nhận.`,to:'/app/reports'},
  {icon:<Medal/>,title:'Thành tích',text:summary.completed_sessions?'Thành tích được tính từ các buổi đã hoàn thành.':'Hoàn thành buổi tập đầu tiên để bắt đầu ghi nhận.',to:'/app/reports'},
  {icon:<History/>,title:'Lịch sử tập luyện',text:'Xem lại các buổi tập và kết quả đã lưu.',to:'/app/history'},
  {icon:<HeartPulse/>,title:'Chỉ số tự khai báo',text:'Quản lý chiều cao và cân nặng do bạn cung cấp.',action:()=>setEditing(true)},
  {icon:<Settings/>,title:'Cài đặt',text:'Ngôn ngữ, thông báo, giao diện và trạng thái AI Coach.',to:'/app/settings'},
  {icon:<Activity/>,title:'Bắt đầu tập luyện',text:'Chọn một trong hai bài tập hệ thống đang hỗ trợ.',to:'/app/exercises'},
 ];
 return <div className="profile-page">
  <section className="surface profile-hero"><div className="profile-identity"><div className="profile-avatar">{profile.avatar_data_url?<img src={profile.avatar_data_url} alt={`Ảnh đại diện của ${profile.full_name}`}/>:<span>{profile.full_name[0]?.toUpperCase()}</span>}<button onClick={()=>{setEditing(true);setTimeout(()=>fileRef.current?.click(),0)}} aria-label="Thay ảnh đại diện"><Camera size={18}/></button></div><div><span className="eyebrow">HỒ SƠ REHABAI</span><h1>{profile.full_name}</h1><p>{profile.bio||'Mỗi bước tiến nhỏ hôm nay đều tạo nên thay đổi lớn ngày mai.'}</p><div className="profile-badges"><span>{summary.completed_sessions} buổi hoàn thành</span><span>{Math.round(summary.completion_rate*100)}% hoàn thành</span></div></div></div><img className="profile-hero-character" src={heroCompanion} alt="" aria-hidden="true"/><button className="btn btn-primary profile-edit" onClick={()=>setEditing(true)}><Pencil size={17}/> Chỉnh sửa hồ sơ</button></section>
  {error&&<p className="form-error" role="alert">{error}</p>}
  <div className="profile-heading"><div><h2>Hồ sơ cá nhân</h2><p>Quản lý thông tin, theo dõi tiến trình và cá nhân hóa trải nghiệm.</p></div></div>
  <section className="profile-card-grid">{cards.map(card=>{const content=<><span className="profile-card-icon">{card.icon}</span><div><h3>{card.title}</h3><p>{card.text}</p></div><ChevronRight size={18}/></>;return card.to?<Link key={card.title} to={card.to} className="surface profile-card">{content}</Link>:<button key={card.title} className="surface profile-card" onClick={card.action}>{content}</button>})}</section>
  <blockquote className="profile-quote">“Mỗi chuyển động nhỏ đều đáng tự hào.”</blockquote>
  {editing&&<div className="profile-edit-overlay" role="dialog" aria-modal="true" aria-labelledby="profile-edit-title"><form className="surface profile-edit-dialog" onSubmit={save}><header><div><span className="eyebrow">CÁ NHÂN HÓA</span><h2 id="profile-edit-title">Chỉnh sửa hồ sơ</h2></div><button type="button" className="icon-button" onClick={()=>{setEditing(false);setForm(asForm(profile));setError('')}} aria-label="Đóng"><X/></button></header><div className="profile-avatar-editor"><div className="profile-avatar large">{form.avatar_data_url?<img src={form.avatar_data_url} alt="Xem trước ảnh đại diện"/>:<span>{form.full_name[0]?.toUpperCase()}</span>}</div><div><button type="button" className="btn btn-secondary" onClick={()=>fileRef.current?.click()}><ImagePlus size={17}/> Chọn ảnh</button>{form.avatar_data_url&&<button type="button" className="text-button inline" onClick={()=>setForm(value=>({...value,avatar_data_url:null}))}>Xóa ảnh</button>}<small>JPEG, PNG hoặc WebP · tối đa 8 MB trước khi tối ưu</small></div><input ref={fileRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseAvatar}/></div><div className="profile-form-grid"><label>Họ và tên<input value={form.full_name} minLength={2} maxLength={160} required onChange={e=>setForm({...form,full_name:e.target.value})}/></label><label>Email<input value={profile.email} disabled/></label><label>Số điện thoại<input value={form.phone} maxLength={32} inputMode="tel" onChange={e=>setForm({...form,phone:e.target.value})}/></label><label>Mục tiêu buổi/tuần<input type="number" min={1} max={14} value={form.weekly_goal} onChange={e=>setForm({...form,weekly_goal:Number(e.target.value)})}/></label><label>Chiều cao (cm)<input type="number" min={50} max={260} step="0.1" value={form.height_cm} onChange={e=>setForm({...form,height_cm:e.target.value})}/></label><label>Cân nặng (kg)<input type="number" min={10} max={500} step="0.1" value={form.weight_kg} onChange={e=>setForm({...form,weight_kg:e.target.value})}/></label><label className="profile-bio-field">Giới thiệu<textarea value={form.bio} maxLength={300} rows={3} onChange={e=>setForm({...form,bio:e.target.value})}/><small>{form.bio.length}/300</small></label></div><footer><button type="button" className="btn btn-secondary" onClick={()=>{setEditing(false);setForm(asForm(profile))}}>Hủy</button><button className="btn btn-primary" disabled={saving}><Save size={17}/>{saving?'Đang lưu…':'Lưu hồ sơ'}</button></footer></form></div>}
 </div>
}
