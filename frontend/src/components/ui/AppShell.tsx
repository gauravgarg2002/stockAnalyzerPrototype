import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { copy } from '../../lib/copy';
import { ROUTES } from '../../lib/routes';
import { GlobalSearch } from './GlobalSearch';
import { Footer } from './Footer';

const NAV = [
  { to: ROUTES.home, label: copy.nav.home, end: true },
  { to: ROUTES.portfolio, label: copy.nav.portfolio, end: false },
  { to: ROUTES.compare, label: copy.nav.compare, end: false },
  { to: ROUTES.watchlist, label: copy.nav.watchlist, end: false },
  { to: ROUTES.connect, label: copy.nav.connect, end: false },
] as const;

function navClass(isActive: boolean): string {
  return `block rounded-lg px-3 py-2 text-base font-medium ${
    isActive ? 'bg-indigo-50 text-indigo-800' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
  }`;
}

export function AppShell() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const isHome = location.pathname === ROUTES.home;

  // New page: close the menu, scroll to top, and let keyboard users start at the content.
  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-slate-800">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:font-medium focus:text-indigo-800 focus:shadow-lg"
      >
        {copy.app.skip}
      </a>

      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-page items-center gap-3 px-4 py-2 sm:px-6">
          <Link to={ROUTES.home} className="flex items-center gap-2 rounded-lg py-1 text-lg font-bold tracking-tight text-slate-900">
            <span
              aria-hidden="true"
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-700 text-white"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 16l5-6 4 3 7-8" />
              </svg>
            </span>
            {copy.app.name}
          </Link>

          <nav aria-label={copy.nav.label} className="ml-4 hidden lg:block">
            <ul className="flex items-center gap-1">
              {NAV.map((n) => (
                <li key={n.to}>
                  <NavLink to={n.to} end={n.end} className={({ isActive }) => navClass(isActive)}>
                    {n.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="ml-auto hidden w-full max-w-sm md:block">
            {!isHome ? <GlobalSearch /> : null}
          </div>

          <button
            ref={menuButton}
            type="button"
            className="ml-auto inline-flex h-11 w-11 items-center justify-center rounded-lg text-slate-800 hover:bg-slate-100 md:ml-2 lg:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? copy.nav.closeMenu : copy.nav.openMenu}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>

        {!isHome ? (
          <div className="mx-auto max-w-page px-4 pb-3 sm:px-6 md:hidden">
            <GlobalSearch />
          </div>
        ) : null}

        <div id="mobile-menu" hidden={!menuOpen} className="border-t border-slate-200 lg:hidden">
          <nav aria-label={copy.nav.label} className="mx-auto max-w-page px-4 py-2 sm:px-6">
            <ul className="space-y-1">
              {NAV.map((n) => (
                <li key={n.to}>
                  <NavLink to={n.to} end={n.end} className={({ isActive }) => navClass(isActive)} onClick={() => setMenuOpen(false)}>
                    {n.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main
        id="main"
        ref={mainRef}
        tabIndex={-1}
        className="mx-auto w-full max-w-page flex-1 px-4 py-6 outline-none sm:px-6 sm:py-8"
      >
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}
