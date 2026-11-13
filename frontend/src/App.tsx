import { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/ui/AppShell';
import { PageSkeleton } from './components/ui/Skeleton';
import { MetaProvider } from './context/MetaContext';
import { ROUTES } from './lib/routes';
import HomePage from './pages/HomePage';
import NotFoundPage from './pages/NotFoundPage';

// Heavier pages (charts, forms) load on demand.
const StockCheckPage = lazy(() => import('./pages/StockCheckPage'));
const FundCheckPage = lazy(() => import('./pages/FundCheckPage'));
const PortfolioPage = lazy(() => import('./pages/PortfolioPage'));
const ConnectPage = lazy(() => import('./pages/ConnectPage'));
const ComparePage = lazy(() => import('./pages/ComparePage'));
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'));
const TryItOnPage = lazy(() => import('./pages/TryItOnPage'));

export default function App() {
  return (
    <MetaProvider>
      <Suspense fallback={<PageSkeleton cards={2} />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path={ROUTES.home} element={<HomePage />} />
            <Route path={ROUTES.connect} element={<ConnectPage />} />
            <Route path={ROUTES.portfolio} element={<PortfolioPage />} />
            <Route path={ROUTES.stock} element={<StockCheckPage />} />
            <Route path={ROUTES.fund} element={<FundCheckPage />} />
            <Route path={ROUTES.compare} element={<ComparePage />} />
            <Route path={ROUTES.watchlist} element={<WatchlistPage />} />
            <Route path={ROUTES.tryIt} element={<TryItOnPage />} />
            <Route path={ROUTES.tryItKind} element={<TryItOnPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </MetaProvider>
  );
}
