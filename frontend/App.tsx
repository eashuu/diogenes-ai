
import React from 'react';
import DemoOne from './demo';
import { ThemeProvider } from './lib/theme-provider';

export default function App() {
  return (
    <ThemeProvider>
      <div className="min-h-screen bg-background">
        <DemoOne />
      </div>
    </ThemeProvider>
  );
}
