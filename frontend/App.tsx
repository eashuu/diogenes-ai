
import React from 'react';
import DemoOne from './demo';
import { ThemeProvider } from './lib/theme-provider';
import { ToastProvider } from './components/ToastProvider';

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <div className="min-h-screen bg-background">
          <DemoOne />
        </div>
      </ToastProvider>
    </ThemeProvider>
  );
}
