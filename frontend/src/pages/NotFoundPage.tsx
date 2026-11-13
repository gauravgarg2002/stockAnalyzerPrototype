import { copy } from '../lib/copy';
import { ROUTES } from '../lib/routes';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { EmptyState } from '../components/ui/EmptyState';
import { LinkButton } from '../components/ui/Button';
import { GlobalSearch } from '../components/ui/GlobalSearch';

export default function NotFoundPage() {
  useDocumentTitle(copy.notFound.title);
  return (
    <div className="mx-auto max-w-xl pt-12">
      <EmptyState title={copy.notFound.title} action={<LinkButton to={ROUTES.home}>{copy.notFound.action}</LinkButton>}>
        <p>{copy.notFound.body}</p>
        <div className="mt-4 text-left">
          <GlobalSearch />
        </div>
      </EmptyState>
    </div>
  );
}
