import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useAuthStore } from '@/stores/authStore';
import { Skeleton } from '@/components/ui/Skeleton';

const Dashboard = lazy(() => import('@/pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Login = lazy(() => import('@/pages/Login').then(m => ({ default: m.Login })));
const RawDataList = lazy(() => import('@/pages/RawData/RawDataList').then(m => ({ default: m.RawDataList })));
const RawDataDetail = lazy(() => import('@/pages/RawData/RawDataDetail').then(m => ({ default: m.RawDataDetail })));
const AnalysisList = lazy(() => import('@/pages/Analysis/AnalysisList').then(m => ({ default: m.AnalysisList })));
const AnalysisDetail = lazy(() => import('@/pages/Analysis/AnalysisDetail').then(m => ({ default: m.AnalysisDetail })));
const DecisionList = lazy(() => import('@/pages/Decisions/DecisionList').then(m => ({ default: m.DecisionList })));
const DecisionApproval = lazy(() => import('@/pages/Decisions/DecisionApproval').then(m => ({ default: m.DecisionApproval })));
const RuleEditor = lazy(() => import('@/pages/Rules/RuleEditor').then(m => ({ default: m.RuleEditor })));
const RuleVersions = lazy(() => import('@/pages/Rules/RuleVersions').then(m => ({ default: m.RuleVersions })));
const Settings = lazy(() => import('@/pages/Settings/Settings').then(m => ({ default: m.Settings })));
const NotFound = lazy(() => import('@/pages/NotFound').then(m => ({ default: m.NotFound })));

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <BrowserRouter><Suspense fallback={<div className="space-y-4 p-6"><Skeleton className="h-10 w-72"/><Skeleton className="h-72 w-full"/></div>}>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="raw-data" element={<RawDataList />} />
          <Route path="raw-data/:id" element={<RawDataDetail />} />
          <Route path="analysis" element={<AnalysisList />} />
          <Route path="analysis/:id" element={<AnalysisDetail />} />
          <Route path="decisions" element={<DecisionList />} />
          <Route path="decisions/:id" element={<DecisionApproval />} />
          <Route path="rules" element={<RuleEditor />} />
          <Route path="rules/versions" element={<RuleVersions />} />
          <Route path="settings/llm" element={<Settings />} />
          <Route path="settings/*" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
          </Route>
        </Route>
      </Routes>
    </Suspense></BrowserRouter>
  );
}

export default App;
