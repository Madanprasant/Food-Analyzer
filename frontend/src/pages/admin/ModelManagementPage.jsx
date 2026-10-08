import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../../lib/api";

export default function ModelManagementPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState(null);
  const [models, setModels] = useState([]);
  const [form, setForm] = useState({ model_name: "", version: "", model: null, class_names: null });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [actionId, setActionId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      await apiRequest("/admin/me");
      const [nextActive, nextModels] = await Promise.all([apiRequest("/admin/models/active"), apiRequest("/admin/models")]);
      setActive(nextActive); setModels(nextModels.models);
    } catch (requestError) {
      if (requestError.status === 401 || requestError.status === 403) navigate("/admin/login");
      else setError(requestError.message);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  function update(name, value) { setForm((current) => ({ ...current, [name]: value })); }
  async function upload(event) {
    event.preventDefault(); setError(""); setNotice("");
    if (!form.model || !form.class_names) { setError("Select both the PyTorch model and class_names.json files."); return; }
    setUploading(true);
    try {
      const body = new FormData(); body.append("model_name", form.model_name); body.append("version", form.version); body.append("architecture", "auto"); body.append("model", form.model); body.append("class_names", form.class_names);
      const saved = await apiRequest("/admin/models", { method: "POST", body });
      setNotice(`${saved.model_name} ${saved.version} was validated and is ready to activate.`);
      setForm({ model_name: "", version: "", model: null, class_names: null }); await load();
    } catch (requestError) { setError(requestError.message); } finally { setUploading(false); }
  }
  async function activate(model, rollback = false) {
    setError(""); setNotice(""); setActionId(model.id);
    try {
      const updated = await apiRequest(`/admin/models/${model.id}/${rollback ? "rollback" : "activate"}`, { method: "POST" });
      setNotice(`${updated.model_name} ${updated.version} is now active.`); await load();
    } catch (requestError) { setError(requestError.message); } finally { setActionId(""); }
  }
  function logout() { localStorage.removeItem("platesignal_access_token"); localStorage.removeItem("platesignal_user"); navigate("/"); }

  return <main className="app-shell"><nav className="app-nav"><Link className="wordmark" to="/dashboard"><span className="wordmark-mark">⌁</span> PLATESIGNAL</Link><div><Link to="/dashboard">User dashboard</Link><button type="button" onClick={logout}>Log out</button></div></nav><section className="admin-page"><div className="dashboard-head"><div><div className="terminal-label">ADMIN / MODEL REGISTRY</div><h1>Model management.</h1><p>New uploads are validated before activation. The active model stays in use until you explicitly switch versions.</p></div></div>{error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="admin-notice" role="status">{notice}</p>}<section className="admin-grid"><article className="admin-card"><div className="terminal-label">ACTIVE MODEL</div>{loading ? <p>Loading registry…</p> : active ? <><h2>{active.model_name}</h2><strong>{active.version}</strong><p>{active.class_count} classes · {active.architecture}</p></> : <p>No active model is registered.</p>}</article><section className="admin-card"><div className="terminal-label">UPLOAD VALIDATED CANDIDATE</div><form className="admin-upload" onSubmit={upload}><label>Model name<input required value={form.model_name} onChange={(event) => update("model_name", event.target.value)} placeholder="e.g. Indian Food Classifier" /></label><label>Version<input required value={form.version} onChange={(event) => update("version", event.target.value)} placeholder="e.g. v2" /></label><label>PyTorch model (.pt or .pth)<input required type="file" accept=".pt,.pth" onChange={(event) => update("model", event.target.files?.[0] || null)} /></label><label>Class mapping (class_names.json)<input required type="file" accept=".json,application/json" onChange={(event) => update("class_names", event.target.files?.[0] || null)} /></label><button className="button" disabled={uploading}>{uploading ? "Validating…" : "Upload & validate ↗"}</button></form></section></section><section className="history-card"><div><div className="terminal-label">MODEL VERSIONS</div><h2>Available versions</h2></div>{!loading && <div className="model-list">{models.map((model) => <article key={model.id}><div><strong>{model.model_name} <small>{model.version}</small></strong><p>{model.class_count} classes · {model.status} · uploaded {new Date(model.uploaded_at).toLocaleDateString()}</p></div>{model.active ? <span className="active-model">Active</span> : <button className="text-button" disabled={actionId === model.id} onClick={() => activate(model, model.is_baseline)}>{actionId === model.id ? "Switching…" : model.is_baseline ? "Roll back" : "Activate"}</button>}</article>)}</div>}</section></section></main>;
}
