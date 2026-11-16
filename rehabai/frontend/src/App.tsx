import { BrowserRouter, Navigate, Routes, Route, useLocation, useParams } from 'react-router-dom';
import { Component, lazy, Suspense } from 'react';
import type { ReactNode } from 'react';
const Home = lazy(() => import('./pages/Home'));
const PublicHome = lazy(() => import('./pages/PublicHome'));
const PublicExercise = lazy(() => import('./pages/PublicExercise'));
const PublicExerciseList = lazy(() => import('./pages/PublicExercise').then(module => ({ default: module.PublicExerciseList })));
const PublicKnowledge = lazy(() => import('./pages/PublicKnowledge'));
const PublicKnowledgeDetail = lazy(() => import('./pages/PublicKnowledge').then(module => ({ default: module.PublicKnowledgeDetail })));
const PublicResearch = lazy(() => import('./pages/PublicResearch'));
const PublicAbout = lazy(() => import('./pages/PublicAbout'));
const PublicFaq = lazy(() => import('./pages/PublicFaq'));
const ExerciseSelection = lazy(() => import('./pages/ExerciseSelection'));
const Practice = lazy(() => import('./pages/Practice'));
const DeepBreathing = lazy(() => import('./pages/DeepBreathing'));
const HistoryPage = lazy(() => import('./pages/History'));
import PatientChat from './components/PatientChat';
const Login = lazy(() => import('./pages/Login'));
const Reports = lazy(() => import('./pages/Reports'));
const SettingsPage = lazy(() => import('./pages/Settings'));
const SessionDetail = lazy(() => import('./pages/SessionDetail'));
import AppShell from './layout/AppShell';
import { AuthProvider, useAuth } from './auth';
import PublicChrome from './components/PublicChrome';
const AICoach = lazy(() => import('./pages/AICoach'));
const Research = lazy(() => import('./pages/Research'));
const Profile = lazy(() => import('./pages/Profile'));
const Admin = lazy(() => import('./pages/Admin'));
const Doctor = lazy(() => import('./pages/Doctor'));
const Clinic = lazy(() => import('./pages/Clinic'));

function PageFallback() {
  return <div className="page-container" role="status" aria-live="polite"><div className="surface loading-state">Đang tải trang…</div></div>;
}

type ChatBoundaryProps = { children: ReactNode };
type ChatBoundaryState = { hasError: boolean };

/** Keep malformed chat data from taking down the authenticated shell. */
class ChatErrorBoundary extends Component<ChatBoundaryProps, ChatBoundaryState> {
  state: ChatBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ChatBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error('RehabAI chat widget crashed', error);
  }

  render() {
    if (this.state.hasError) {
      return <div className="chat-crash-fallback" role="alert">Chatbot tạm thời gặp lỗi. Bạn vẫn có thể dùng các chức năng khác của ứng dụng. <button type="button" onClick={() => this.setState({ hasError: false })}>Thử lại</button></div>;
    }
    return this.props.children;
  }
}

function PrivateExerciseRedirect() { const { slug } = useParams(); if (slug === 'deep-breathing') return <DeepBreathing />; const exerciseId = slug === 'hand-opening' ? 4 : slug === 'elbow-extension' ? 2 : slug === 'neck-lateral-stretch' ? 6 : null; return <Navigate to={exerciseId ? `/app/practice/${exerciseId}` : '/app/exercises'} replace />; }
function LegacyPracticeRedirect() { const { id } = useParams(); return <Navigate to={`/app/practice/${encodeURIComponent(id || '')}`} replace />; }
function LegacyHistoryRedirect() { const { id } = useParams(); return <Navigate to={id ? `/app/history/${encodeURIComponent(id)}` : '/app/history'} replace />; }

function AppRoutes() {
  const location = useLocation();
  const { user } = useAuth();
  const publicPath = location.pathname === '/' || location.pathname === '/login' || location.pathname === '/register'
    || location.pathname === '/about' || location.pathname === '/faq' || location.pathname === '/research'
    || location.pathname === '/exercises' || location.pathname.startsWith('/exercises/')
    || location.pathname === '/knowledge' || location.pathname.startsWith('/knowledge/');
  if (publicPath) return <PublicChrome><Suspense fallback={<PageFallback />}><Routes>
    <Route path="/" element={<PublicHome/>}/><Route path="/about" element={<PublicAbout/>}/><Route path="/faq" element={<PublicFaq/>}/>
    <Route path="/login" element={<Login/>}/><Route path="/register" element={<Login/>}/>
    <Route path="/exercises" element={<PublicExerciseList/>}/><Route path="/exercises/:slug" element={<PublicExercise/>}/>
    <Route path="/knowledge" element={<PublicKnowledge/>}/><Route path="/knowledge/:slug" element={<PublicKnowledgeDetail/>}/>
    <Route path="/research" element={<PublicResearch/>}/>
  </Routes></Suspense></PublicChrome>;
  if (!user) return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  const role = user.role || 'patient';
  const isStaff = role === 'admin' || role === 'doctor';
  return (
    <AppShell><Suspense fallback={<PageFallback />}><div key={location.pathname} className="page-container route-transition">
        <Routes>
          <Route path="/admin" element={<Admin />} />
          <Route path="/doctor" element={<Doctor />} />
          <Route path="/app" element={isStaff ? <Navigate to={role === 'admin' ? '/admin' : '/doctor'} replace /> : <Home />} />
          <Route path="/app/exercises" element={<ExerciseSelection />} />
          <Route path="/app/exercises/:slug" element={<PrivateExerciseRedirect />} />
          <Route path="/app/session/deep-breathing" element={<DeepBreathing />} />
          <Route path="/app/practice/:id" element={<Practice />} />
          <Route path="/app/clinic" element={<Clinic />} />
          <Route path="/app/history" element={<HistoryPage />} />
          <Route path="/app/history/:id" element={<SessionDetail />} />
          <Route path="/app/reports" element={<Reports />} />
          <Route path="/app/ai-coach" element={<AICoach />} />
          <Route path="/app/research" element={<Research />} />
          <Route path="/app/settings" element={<SettingsPage />} />
          <Route path="/app/profile" element={<Profile />} />
          <Route path="/practice/:id" element={<LegacyPracticeRedirect />} />
          <Route path="/history" element={<LegacyHistoryRedirect />} />
          <Route path="/history/:id" element={<LegacyHistoryRedirect />} />
          <Route path="/reports" element={<Navigate to="/app/reports" replace />} />
          <Route path="/ai-coach" element={<Navigate to="/app/ai-coach" replace />} />
          <Route path="/settings" element={<Navigate to="/app/settings" replace />} />
          <Route path="/profile" element={<Navigate to="/app/profile" replace />} />
        </Routes>
      </div></Suspense>
      <ChatErrorBoundary><PatientChat /></ChatErrorBoundary>
    </AppShell>
  );
}

function App() { return <BrowserRouter><AuthProvider><AppRoutes/></AuthProvider></BrowserRouter>; }

export default App;
