import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { Dashboard } from '@/pages/Dashboard';
import { Login } from '@/pages/Login';
import { RawDataList } from '@/pages/RawData/RawDataList';
import { RawDataDetail } from '@/pages/RawData/RawDataDetail';
import { AnalysisList } from '@/pages/Analysis/AnalysisList';
import { AnalysisDetail } from '@/pages/Analysis/AnalysisDetail';
import { DecisionList } from '@/pages/Decisions/DecisionList';
import { DecisionApproval } from '@/pages/Decisions/DecisionApproval';
import { RuleEditor } from '@/pages/Rules/RuleEditor';
import { RuleVersions } from '@/pages/Rules/RuleVersions';
import { Settings } from '@/pages/Settings/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;