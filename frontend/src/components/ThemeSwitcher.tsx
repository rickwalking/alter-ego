import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

/**
 * Theme Switcher Component
 *
 * Toggles between Cyber Purple and Electric Blue themes
 * Theme is persisted in localStorage
 */
export function ThemeSwitcher() {
  const [theme, setTheme] = useState<'cyber-purple' | 'electric-blue'>('cyber-purple');

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') as 'cyber-purple' | 'electric-blue' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    }
  }, []);

  const applyTheme = (newTheme: 'cyber-purple' | 'electric-blue') => {
    const root = document.documentElement;
    if (newTheme === 'electric-blue') {
      root.setAttribute('data-theme', 'electric-blue');
    } else {
      root.removeAttribute('data-theme');
    }
  };

  const toggleTheme = () => {
    const newTheme = theme === 'cyber-purple' ? 'electric-blue' : 'cyber-purple';
    setTheme(newTheme);
    applyTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '2rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 50,
      }}
    >
      <Button
        onClick={toggleTheme}
        className="glass-button-primary cursor-pointer"
        size="lg"
        aria-label={`Switch to ${theme === 'cyber-purple' ? 'Electric Blue' : 'Cyber Purple'} theme`}
      >
        {theme === 'cyber-purple' ? '⚡ Electric Blue' : '💜 Cyber Purple'}
      </Button>
    </div>
  );
}
