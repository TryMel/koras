"use client";

import React, { FormEvent, useCallback, useEffect, useState } from "react";

type Tab = "simulation" | "audit" | "devices" | "users" | "transactions";
type RecordValue = Record<string, unknown>;
type Metrics = {
  users: number;
  trusted_devices: number;
  policy_denials: number;
  intent_accuracy: number | null;
  false_action_rate: number | null;
  metrics_note: string;
};

const apiBase = (process.env.NEXT_PUBLIC_KORAS_API_URL ?? "http://127.0.0.1:8000/api/v1")
  .replace(/\/$/, "");

async function apiRequest<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail ?? `Erreur API (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export default function AdminDashboard() {
  const [token, setToken] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [adminName, setAdminName] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("simulation");
  const [simQuery, setSimQuery] = useState("Envoie 5000 francs à maman");
  const [simVulnerable, setSimVulnerable] = useState(false);
  const [simBattery, setSimBattery] = useState(85);
  const [simOffline, setSimOffline] = useState(false);
  const [simResult, setSimResult] = useState<RecordValue | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [records, setRecords] = useState<RecordValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadData = useCallback(async (selectedTab: Tab, accessToken: string) => {
    setLoading(true);
    setError("");
    try {
      if (selectedTab === "simulation") {
        const values = await apiRequest<Metrics>("/admin/metrics", accessToken);
        setMetrics(values);
        return;
      }
      const endpoint = {
        audit: "/admin/audit",
        devices: "/admin/devices",
        users: "/admin/users",
        transactions: "/admin/transactions",
        simulation: "/admin/metrics",
      }[selectedTab];
      setRecords(await apiRequest<RecordValue[]>(endpoint, accessToken));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("koras_admin_token");
    if (savedToken) {
      setToken(savedToken);
      void apiRequest<RecordValue>("/users/me", savedToken)
        .then((profile) => {
          if (profile.role !== "admin" && profile.role !== "super_admin") {
            throw new Error("Ce compte ne dispose pas des droits d'administration.");
          }
          setAdminName(display(profile.display_name ?? profile.phone));
          void loadData("simulation", savedToken);
        })
        .catch((requestError: unknown) => {
          window.localStorage.removeItem("koras_admin_token");
          setToken("");
          setError(requestError instanceof Error ? requestError.message : "Session invalide.");
        });
    }
  }, [loadData]);

  useEffect(() => {
    if (token) void loadData(activeTab, token);
  }, [activeTab, loadData, token]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ phone: phone.trim(), password }),
      });
      const data = await response.json() as { access_token?: string; detail?: string };
      if (!response.ok || !data.access_token) {
        throw new Error(data.detail ?? "Connexion impossible.");
      }
      const profile = await apiRequest<RecordValue>(
        "/users/me",
        data.access_token,
      );
      if (profile.role !== "admin" && profile.role !== "super_admin") {
        throw new Error("Ce compte ne dispose pas des droits d'administration.");
      }
      window.localStorage.setItem("koras_admin_token", data.access_token);
      setAdminName(display(profile.display_name ?? profile.phone));
      setToken(data.access_token);
      setPassword("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Connexion impossible.");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    try {
      await apiRequest<void>("/auth/logout", token, { method: "POST" });
    } catch {
      // The local session is still cleared if it has already expired server-side.
    }
    window.localStorage.removeItem("koras_admin_token");
    setToken("");
    setMetrics(null);
    setRecords([]);
  }

  async function handleSimulate() {
    setLoading(true);
    setError("");
    try {
      setSimResult(await apiRequest<RecordValue>("/admin/simulation/run", token, {
        method: "POST",
        body: JSON.stringify({
          simulated_query: simQuery,
          vulnerable_user: simVulnerable,
          battery_level: simBattery,
          is_offline: simOffline,
        }),
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Simulation impossible.");
    } finally {
      setLoading(false);
    }
  }

  async function revokeDevice(deviceId: string) {
    if (!window.confirm("Révoquer cet appareil et terminer ses sessions ?")) return;
    try {
      await apiRequest(`/admin/devices/${encodeURIComponent(deviceId)}/revoke`, token, {
        method: "POST",
      });
      await loadData("devices", token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Révocation impossible.");
    }
  }

  if (!token) {
    return (
      <main className="container">
        <article>
          <h1>KORAS — Administration</h1>
          <p>Connectez-vous avec un compte administrateur KORAS.</p>
          {error && <p role="alert" style={{ color: "#ef4444" }}>{error}</p>}
          <form onSubmit={signIn}>
            <label>
              Numéro de téléphone
              <input autoComplete="username" value={phone} onChange={(event) => setPhone(event.target.value)} required />
            </label>
            <label>
              Mot de passe
              <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            </label>
            <button disabled={loading} type="submit">{loading ? "Connexion…" : "Se connecter"}</button>
          </form>
        </article>
      </main>
    );
  }

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "simulation", label: "Sandbox" },
    { id: "audit", label: "Audit" },
    { id: "devices", label: "Appareils" },
    { id: "users", label: "Utilisateurs" },
    { id: "transactions", label: "Transactions" },
  ];

  return (
    <main className="container">
      <header className="header-nav">
        <div>
          <h2>KORAS — Administration & Supervision</h2>
          <small>Connecté : {adminName}</small>
        </div>
        <button className="secondary" onClick={() => void signOut()}>Se déconnecter</button>
      </header>

      {error && <article role="alert" style={{ borderColor: "#ef4444" }}>{error}</article>}

      <nav aria-label="Sections d'administration">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "primary" : "secondary"}
            onClick={() => setActiveTab(tab.id)}
            style={{ marginRight: 8 }}
          >
            {tab.label}
          </button>
        ))}
        <button className="secondary" disabled={loading} onClick={() => void loadData(activeTab, token)}>
          Actualiser
        </button>
      </nav>

      {activeTab === "simulation" && (
        <>
          <section className="grid" style={{ margin: "1rem 0" }}>
            <article><small>Utilisateurs</small><h3>{metrics?.users ?? "—"}</h3></article>
            <article><small>Appareils approuvés</small><h3>{metrics?.trusted_devices ?? "—"}</h3></article>
            <article><small>Refus de politique</small><h3>{metrics?.policy_denials ?? "—"}</h3></article>
            <article><small>Précision mesurée</small><h3>{metrics?.intent_accuracy === null ? "Non mesurée" : `${metrics?.intent_accuracy ?? "—"}%`}</h3></article>
          </section>
          {metrics && <small>{metrics.metrics_note}</small>}
          <article>
            <h4>Simulateur d'agent (sans exécution réelle)</h4>
            <label>
              Commande
              <input value={simQuery} onChange={(event) => setSimQuery(event.target.value)} />
            </label>
            <div className="grid">
              <label>
                Batterie ({simBattery}%)
                <input type="range" min="1" max="100" value={simBattery} onChange={(event) => setSimBattery(Number(event.target.value))} />
              </label>
              <label><input type="checkbox" checked={simOffline} onChange={(event) => setSimOffline(event.target.checked)} /> Hors ligne</label>
              <label><input type="checkbox" checked={simVulnerable} onChange={(event) => setSimVulnerable(event.target.checked)} /> Mode protection renforcée</label>
            </div>
            <button disabled={loading || !simQuery.trim()} onClick={() => void handleSimulate()}>
              {loading ? "Exécution…" : "Lancer la simulation"}
            </button>
            {simResult && <pre style={{ background: "#0a0c12", padding: 16, borderRadius: 8, overflowX: "auto" }}>{JSON.stringify(simResult, null, 2)}</pre>}
          </article>
        </>
      )}

      {activeTab !== "simulation" && (
        <article>
          <h4>{tabs.find((tab) => tab.id === activeTab)?.label}</h4>
          {loading ? <p aria-live="polite">Chargement…</p> : records.length === 0 ? <p>Aucune donnée enregistrée.</p> : (
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead><tr>{Object.keys(records[0]).map((key) => <th key={key}>{key}</th>)}{activeTab === "devices" && <th>Actions</th>}</tr></thead>
                <tbody>
                  {records.map((record, index) => (
                    <tr key={display(record.id ?? record.resource_id ?? index)}>
                      {Object.entries(record).map(([key, value]) => <td key={key}>{display(value)}</td>)}
                      {activeTab === "devices" && (
                        <td>
                          {record.trust_status === "trusted" && typeof record.id === "string"
                            ? <button className="secondary" onClick={() => void revokeDevice(record.id as string)}>Révoquer</button>
                            : "—"}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}
    </main>
  );
}
