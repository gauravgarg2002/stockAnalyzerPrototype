/** The lens mark: a marigold tile holding a ring and a rising line. */
export function LogoMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`relative inline-flex items-center justify-center rounded-xl bg-marigold-400 text-peacock-900 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-[78%] w-[78%]" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="16" cy="16" r="9.5" />
        <path d="M10.5 18.5l3.5-4 3 2.5 4.5-6" />
      </svg>
    </span>
  );
}
