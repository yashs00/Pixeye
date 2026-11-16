import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/common/Sidebar';
import Navbar from './components/common/Navbar';
import QuestionBankPage from './pages/QuestionBankPage';
import SelectedQuestionsPage from './pages/SelectedQuestionsPage';
import ImportHistoryPage from './pages/ImportHistoryPage';
import OverviewPage from './pages/OverviewPage';
import SettingsPage from './pages/SettingsPage';
import VariantStudioPage from './pages/VariantStudioPage';
import { SelectionProvider } from './context/SelectionContext';

export default function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  return (
    <SelectionProvider>
      <BrowserRouter>
        <Routes>
          {/* Variant Studio: full-screen focused workspace (no sidebar) */}
          <Route path="/studio/:questionId" element={<VariantStudioPage />} />
          <Route path="*" element={
        <div className="flex min-h-screen bg-slate-50 text-slate-800">
          {/* Persistent Sidebar */}
          <Sidebar />

          {/* Main Area */}
          <div className="flex-1 flex flex-col min-w-0">
            <Navbar
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              onOpenSelectionDrawer={() => setIsDrawerOpen(true)}
            />

            <main className="p-6 flex-1 max-w-7xl w-full mx-auto">
              <Routes>
                <Route
                  path="/"
                  element={
                    <QuestionBankPage
                      searchTerm={searchTerm}
                      isDrawerOpen={isDrawerOpen}
                      onOpenDrawer={() => setIsDrawerOpen(true)}
                      onCloseDrawer={() => setIsDrawerOpen(false)}
                    />
                  }
                />
                <Route path="/selected" element={<SelectedQuestionsPage />} />
                <Route path="/imports" element={<ImportHistoryPage />} />
                <Route path="/overview" element={<OverviewPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
        </div>
          } />
        </Routes>
      </BrowserRouter>
    </SelectionProvider>
  );
}

