import React from 'react';
import { AuthProvider } from './hooks/useAuth';
import { LanguageProvider } from './contexts/LanguageContext';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <LanguageProvider>
        <div className="App">
          {/* O roteamento agora é gerenciado pelo main.tsx */}
        </div>
      </LanguageProvider>
    </AuthProvider>
  );
};

export default App; 