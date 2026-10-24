import { useEffect, useState } from "react";

type ApiState = "checking" | "reachable" | "unreachable";

export function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((body) => setApiState(body.status === "ok" ? "reachable" : "unreachable"))
      .catch(() => setApiState("unreachable"));
  }, []);

  return (
    <main>
      <h1>Funda Griller</h1>
      <p role="status">API: {apiState}</p>
    </main>
  );
}
