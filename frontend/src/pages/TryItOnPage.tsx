import { Link, useNavigate, useParams } from 'react-router-dom';
import { copy } from '../lib/copy';
import { checkPath, parseKind, tryPath } from '../lib/routes';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { TryItOnPanel } from '../components/TryItOnPanel';

export default function TryItOnPage() {
  useDocumentTitle(copy.tryIt.title);
  const navigate = useNavigate();
  const params = useParams();
  const kind = parseKind(params.kind);
  const id = params.id ?? null;
  const valid = kind !== null && id !== null;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title={copy.tryIt.title} subtitle={copy.tryIt.subtitle} />
      <Card>
        <TryItOnPanel
          kind={valid ? kind : null}
          id={valid ? id : null}
          onPick={(k, i) => navigate(tryPath(k, i), { replace: true })}
        />
      </Card>
      {valid ? (
        <p className="mt-4 text-sm">
          <Link className="font-medium text-indigo-700 underline underline-offset-2" to={checkPath(kind, id)}>
            {copy.tryIt.backToCheck}
          </Link>
        </p>
      ) : null}
    </div>
  );
}
