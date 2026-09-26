import { createContext, useContext, ReactNode } from 'react';

// Contexto para compartilhar o estado de loading
const NavigationLoadingContext = createContext<{
  isLoading: boolean;
}>({ isLoading: false });

export const useNavigationLoading = () => useContext(NavigationLoadingContext);

// Provider que gerencia o estado de loading
export function NavigationLoadingProvider({ children }: { children: ReactNode }) {
  return (
    <NavigationLoadingContext.Provider value={{ isLoading: false }}>
      {children}
    </NavigationLoadingContext.Provider>
  );
}

// Componente legado para compatibilidade
export function NavigationLoader() {
  return <NavigationLoadingProvider><></></NavigationLoadingProvider>;
}

