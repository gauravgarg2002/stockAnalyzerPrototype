import { Link } from 'react-router-dom';
import type { WatchlistItem } from '../lib/api-types';

/** Compact rows for the Home screen: name, latest price, the person's note. */
export function WatchlistRows({ items }: { items: WatchlistItem[] }) {
  return (
    <ul className="divide-y divide-dashed divide-slate-200">
      {items.map((it) => (
        <li key={it.id} className="-mx-3 rounded-xl px-3 py-3.5 transition-colors hover:bg-lagoon-100/60">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <Link to={it.checkPath} className="link-draw">
              {it.name}
            </Link>
            {it.latest ? (
              <span className="text-sm tabular-nums text-slate-800">
                {it.latest.label}: <span className="font-semibold">{it.latest.display}</span>
              </span>
            ) : null}
          </div>
          <p className="text-sm text-slate-600">{it.subtitle}</p>
          {it.note ? <p className="mt-1.5 border-l-2 border-marigold-400 pl-3 italic text-slate-800">“{it.note}”</p> : null}
        </li>
      ))}
    </ul>
  );
}
