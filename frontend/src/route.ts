/** The screens as URL hashes: `#/`, `#/koperprofiel`, `#/woning/<id>` and `#/woning/<id>/oordeel`. */

export type Route =
  | { view: "woningen" }
  | { view: "koperprofiel" }
  | { view: "dossier"; fundaId: string }
  | { view: "oordeel"; fundaId: string };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "koperprofiel") return { view: "koperprofiel" };
  if (parts[0] === "woning" && parts[1]) {
    return parts[2] === "oordeel" ? { view: "oordeel", fundaId: parts[1] } : { view: "dossier", fundaId: parts[1] };
  }
  return { view: "woningen" };
}

export function href(route: Route): string {
  switch (route.view) {
    case "woningen":
      return "#/";
    case "koperprofiel":
      return "#/koperprofiel";
    case "dossier":
      return `#/woning/${encodeURIComponent(route.fundaId)}`;
    case "oordeel":
      return `#/woning/${encodeURIComponent(route.fundaId)}/oordeel`;
  }
}
