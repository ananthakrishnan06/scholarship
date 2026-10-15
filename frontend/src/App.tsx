import { useEffect, useState } from "react";
import { api } from "./api";
import Assistant from "./Assistant";
import Workspace from "./Workspace";
import Dashboard from "./Dashboard";
import ScholarshipDetail from "./ScholarshipDetail";
import ScholarshipList from "./ScholarshipList";
import type { Citation, Scheme } from "./types";

export default function App() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || "/");
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [detail, setDetail] = useState<{
    scholarship: Scheme;
    citation: Citation;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    sessionStorage.removeItem("scholar-profile");
    const onHash = () => setRoute(window.location.hash.slice(1) || "/");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    if (route === "/profile") window.location.hash = "/assistant";
  }, [route]);
  useEffect(() => {
    let active = true;
    api<{ results: Scheme[] }>("/scholarships/search", { top_k: 16 })
      .then((d) => {
        if (active) setSchemes(d.results);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const schemeId = route.startsWith("/scholarships/")
    ? decodeURIComponent(route.split("/")[2])
    : undefined;
  useEffect(() => {
    if (!schemeId) {
      setDetail(null);
      return;
    }
    let active = true;
    setBusy(true);
    setError("");
    api<{ scholarship: Scheme; citation: Citation }>(
      "/scholarships/" + encodeURIComponent(schemeId),
    )
      .then((d) => {
        if (active) setDetail(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [schemeId]);
  async function discover(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api<{ results: Scheme[] }>("/scholarships/search", {
        question: search,
        top_k: 16,
      });
      setSchemes(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search unavailable.");
    } finally {
      setBusy(false);
    }
  }
  const title =
    route === "/assistant"
      ? "Let’s find some clarity"
      : route.startsWith("/scholarships")
        ? "Explore your opportunities"
        : "Your next chapter starts here";
  return (
    <Workspace route={route} title={title}>
      {error && (
        <div className="error" role="alert">
          {error}{" "}
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}
      {busy && (
        <p role="status" className="loading">
          Loading scholarship information…
        </p>
      )}
      {route === "/" && <Dashboard schemes={schemes} />}
      {route === "/assistant" && <Assistant />}
      {schemeId && detail && (
        <ScholarshipDetail detail={detail} schemeId={schemeId} />
      )}
      {(route === "/" || route === "/scholarships") && (
        <ScholarshipList
          route={route}
          schemes={schemes}
          search={search}
          setSearch={setSearch}
          busy={busy}
          error={error}
          discover={discover}
        />
      )}
    </Workspace>
  );
}
