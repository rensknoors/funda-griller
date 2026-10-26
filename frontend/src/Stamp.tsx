import { ArrowLeftRight, Calculator, Globe, Landmark, Newspaper, Quote, ScanEye } from "lucide-react";
import type { ReactNode } from "react";

/** Where a fact came from. Each kind has its own icon and border style (double for a register,
 * dotted for a seller's claim, dashed for an estimate), so it reads without colour. */
export type StampKind = "listing" | "official" | "third-party" | "finding" | "observation" | "computed" | "comparable";

const ICONS: Record<StampKind, typeof Landmark> = {
  listing: Newspaper,
  official: Landmark,
  "third-party": Globe,
  finding: Quote,
  observation: ScanEye,
  computed: Calculator,
  comparable: ArrowLeftRight,
};

export const STAMP_LEGEND: [StampKind, string, string][] = [
  ["listing", "Advertentie", "volgens funda"],
  ["official", "Register", "officieel"],
  ["third-party", "Derde partij", "onofficieel"],
  ["finding", "Verkoper", "controleer het origineel"],
  ["observation", "Foto's", "geschat door model"],
  ["computed", "Berekend", "uit andere feiten"],
  ["comparable", "Vergelijkbaar", "andere woning"],
];

export function Stamp(props: {
  kind: StampKind;
  /** The full sentence a screen reader hears instead of the visible shorthand. */
  label?: string;
  href?: string;
  title?: string;
  children: ReactNode;
}) {
  const Icon = ICONS[props.kind];
  const className = `stamp stamp-${props.kind}`;
  const content = (
    <>
      <Icon size={13} strokeWidth={2} aria-hidden="true" className="stamp-icon" />
      <span>{props.children}</span>
    </>
  );
  if (props.href) {
    return (
      <a className={className} href={props.href} target="_blank" rel="noreferrer" aria-label={props.label} title={props.title}>
        {content}
      </a>
    );
  }
  return (
    <span className={className} aria-label={props.label} title={props.title}>
      {content}
    </span>
  );
}
