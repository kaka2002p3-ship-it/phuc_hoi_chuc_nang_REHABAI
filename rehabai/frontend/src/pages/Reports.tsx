import { useEffect, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, CheckCircle2, Droplets, TrendingUp } from 'lucide-react';
import type { ReactNode } from 'react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Summary={total_sessions:number;completed_sessions:number;completion_rate:number;average_pain:number|null};
type Point={date:string;sessions:number;completion_rate:number;average_pain:number|null};
export default function Reports(){
 const {token}=useAuth();
 const [summary,setSummary]=useState<Summary|null>(null); const [points,setPoints]=useState<Point[]>([]); const [days,setDays]=useState(30);
 useEffect(()=>{const headers=authHeaders(token);fetch('/api/reports/summary',{headers}).then(r=>r.json()).then(setSummary);fetch(`/api/reports/progress?days=${days}`,{headers}).then(r=>r.json()).then(setPoints)},[days,token]);
 const chart=points.map(x=>({...x,label:new Date(x.date).toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit'}),completion:Math.round(x.completion_rate*100)}));
 return <div><PageTitle title="Tiến bộ phục hồi" subtitle="Theo dõi tính đều đặn, tỷ lệ hoàn thành và mức đau đã ghi nhận." />
 <div className="range-tabs">{[7,30,90].map(x=><button className={days===x?'active':''} onClick={()=>setDays(x)} key={x}>{x} ngày</button>)}</div>
 <div className="metric-grid"><Metric icon={<Activity/>} label="Tổng buổi tập" value={summary?.total_sessions ?? 0}/><Metric icon={<CheckCircle2/>} label="Tỷ lệ hoàn thành" value={`${Math.round((summary?.completion_rate||0)*100)}%`}/><Metric icon={<Droplets/>} label="Mức đau trung bình" value={summary?.average_pain == null?'Chưa có':`${summary.average_pain}/10`}/><Metric icon={<TrendingUp/>} label="Buổi hoàn thành" value={summary?.completed_sessions ?? 0}/></div>
 <section className="surface chart-card"><div className="section-heading"><div><h3>Tiến bộ theo thời gian</h3><p>Dữ liệu lấy từ các buổi tập đã lưu, không phải dữ liệu minh họa.</p></div></div><div className="chart-area"><ResponsiveContainer><AreaChart data={chart}><defs><linearGradient id="green" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#21866a" stopOpacity=".35"/><stop offset="1" stopColor="#21866a" stopOpacity="0"/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#e4eee9"/><XAxis dataKey="label"/><YAxis domain={[0,100]}/><Tooltip/><Area type="monotone" dataKey="completion" name="Hoàn thành (%)" stroke="#21866a" fill="url(#green)" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></section>
 </div>;
}
export function PageTitle({title,subtitle}:{title:string;subtitle:string}){return <header className="page-title"><span className="eyebrow">REHABAI · THEO DÕI TẠI NHÀ</span><h1>{title}</h1><p>{subtitle}</p></header>}
function Metric({icon,label,value}:{icon:ReactNode;label:string;value:string|number}){return <article className="surface metric-card"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></article>}
