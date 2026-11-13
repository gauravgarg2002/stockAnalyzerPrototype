import { Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { copy } from '../../lib/copy';
import { ROUTES } from '../../lib/routes';
import { GlobalSearch } from './GlobalSearch';
import { Footer } from './Footer';
import { PageSkeleton } from './Skeleton';
import { LogoMark } from './LogoMark';

const NAV = [
  { to: ROUTES.home, label: copy.nav.home, end: true },
  { to: ROUTES.portfolio, label: copy.nav.portfolio, end: false },
  { to: ROUTES.compare, label: copy.nav.compare, end: false },
  { to: ROUTES.watchlist, label: copy.nav.watchlist, end: false },
  { to: ROUTES.connect, label: copy.nav.connect, end: false },
] as const;

/** Desktop nav with a marigold marker that slides to the active page. */
function DesktopNav() {
  const location = useLocation();
  const listRef = useRef<HTMLUListElement>(null);
  const [marker, setMarker] = useState<{ left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    function place() {
      const active = listRef.current?.querySelector<HTMLAnchorElement>('a[aria-current="page"]');
      if (!active || !listRef.current) {
        setMarker(null);
        return;
      }
      const base = listRef.current.getBoundingClientRect();
      const r = active.getBoundingClientRect();
      setMarker({ left: r.left - base.left + 12, width: r.width - 24 });
    }
    place();
    window.addEventListener('resize', place);
    document.fonts?.ready.then(place).catch(() => undefined);
    return () => window.removeEventListener('resize', place);
  }, [location.pathname]);

  return (
    <nav aria-label={copy.nav.label} className="ml-6 hidden lg:block">
      <ul ref={listRef} className="relative flex items-center gap-1">
        {NAV.map((n) => (
          <li key={n.to}>
            <NavLink
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-[0.95rem] font-semibold transition-colors ${
                  isActive ? 'text-white' : 'text-lagoon-200/80 hover:text-white'
                }`
              }
            >
              {n.label}
            </NavLink>
          </li>
        ))}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-1 h-[3px] rounded-full bg-marigold-400 transition-[left,width,opacity] duration-300 ease-out"
          style={{ left: marker?.left ?? 0, width: marker?.width ?? 0, opacity: marker ? 1 : 0 }}
        />
      </ul>
    </nav>
  );
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
    <div className="flex min-h-screen flex-col overflow-x-clip bg-paper text-slate-800">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:font-semibold focus:text-peacock-900 focus:shadow-lift"
      >
        {copy.app.skip}
      </a>

      <header className={`jali sticky top-0 z-30 text-white ${isHome ? '' : 'border-b border-white/10'}`}>
        <div className="mx-auto flex max-w-page items-center gap-3 px-4 py-3 sm:px-6">
          <Link to={ROUTES.home} className="group flex items-center gap-2.5 rounded-lg py-0.5">
            <LogoMark className="h-9 w-9 transition-transform duration-300 group-hover:rotate-[-8deg] group-hover:scale-105" />
            <span className="font-display text-xl font-extrabold tracking-tight">{copy.app.name}</span>
          </Link>

          <DesktopNav />

          <div className="ml-auto hidden w-full max-w-sm md:block">
            {!isHome ? <GlobalSearch tone="dark" shortcut /> : null}
          </div>

          <button
            ref={menuButton}
            type="button"
            className="ml-auto inline-flex h-11 w-11 items-center justify-center rounded-lg text-white hover:bg-white/10 md:ml-2 lg:hidden"
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
            <GlobalSearch tone="dark" />
          </div>
        ) : null}

        <div id="mobile-menu" hidden={!menuOpen} className="border-t border-white/10 lg:hidden">
          <nav aria-label={copy.nav.label} className="mx-auto max-w-page px-4 py-2 sm:px-6">
            <ul className="space-y-1">
              {NAV.map((n, i) => (
                <li key={n.to} className="animate-rise" style={{ animationDelay: `${i * 40}ms` } as CSSProperties}>
                  <NavLink
                    to={n.to}
                    end={n.end}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg px-3 py-2.5 text-base font-semibold ${
                        isActive ? 'bg-white/10 text-white' : 'text-lagoon-200 hover:bg-white/5 hover:text-white'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span aria-hidden="true" className={`h-2 w-2 rounded-full ${isActive ? 'bg-marigold-400' : 'bg-white/20'}`} />
                        {n.label}
                      </>
                    )}
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
        className={`mx-auto w-full flex-1 outline-none ${isHome ? '' : 'max-w-page px-4 pb-10 sm:px-6'}`}
      >
        <Suspense fallback={<div className={isHome ? 'mx-auto max-w-page px-4 py-8 sm:px-6' : 'py-8'}><PageSkeleton cards={2} /></div>}>
          <div key={location.pathname} className="animate-fade">
            <Outlet />
          </div>
        </Suspense>
      </main>

      <Footer />
    </div>
  );
}
