'use client';

import { useAuth } from '@/context/AuthContext';
import ThemeToggle from '@/components/common/ThemeToggle';
import { Menu } from 'lucide-react';

interface HeaderProps {
  onMenuClick: () => void;
  title?: string;
}

export default function Header({ onMenuClick, title = 'Dashboard' }: HeaderProps) {
  const { user } = useAuth();

  return (
    <header className="bg-white dark:bg-stone-900 border-b border-stone-200 dark:border-stone-800 h-14 flex items-center justify-between px-4 lg:px-6 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-md text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
          aria-label="Abrir menú"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-sm font-semibold text-stone-800 dark:text-stone-100">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />

        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-stone-200 dark:border-stone-800 ml-1">
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-semibold">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div className="hidden md:block text-right">
            <p className="text-xs font-medium text-stone-700 dark:text-stone-200 leading-tight">{user?.full_name}</p>
            <p className="text-xs text-stone-400 dark:text-stone-500">{user?.roles?.[0]?.name ?? 'Usuario'}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
