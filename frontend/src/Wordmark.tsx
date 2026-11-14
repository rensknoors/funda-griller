/**
 * The Funda Griller mark: the G-gevel, a geometric G drawn as a house
 * with a pitched roof.
 */
export function GrillerMark(props: { className?: string }) {
  return (
    <svg className={props.className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M19.5 9 12 3 4.5 9v12.5h15V13H12.5" fill="none" stroke="currentColor" strokeWidth="3" />
    </svg>
  );
}
