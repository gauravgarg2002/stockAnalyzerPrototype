import { copy } from '../../lib/copy';
import { Badge } from './Badge';

/** Small badge shown whenever a response has sampleData: true. */
export function SampleDataBadge({ show }: { show: boolean | undefined }) {
  if (!show) return null;
  return (
    <span title={copy.common.sampleDataHint}>
      <Badge tone="accent">{copy.common.sampleData}</Badge>
    </span>
  );
}
