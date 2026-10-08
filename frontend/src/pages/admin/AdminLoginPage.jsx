import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, saveSession } from "../../lib/api";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setError(""); setLoading(true);
    try {
      const session = await apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      saveSession(session);
      await apiRequest("/admin/me");
      navigate("/admin/models");
    } catch (requestError) {
      localStorage.removeItem("platesignal_access_token"); localStorage.removeItem("platesignal_user");
      setError(requestError.status === 403 ? "This account does not have administrator access." : requestError.message);
    } finally { setLoading(false); }
  }

  return <main className="auth-shell"><Link className="wordmark" to="/"><span className="wordmark-mark">⌁</span> PLATESIGNAL</Link><section className="auth-panel"><div className="terminal-label">ADMINISTRATOR ACCESS</div><h1>Manage model versions.</h1><p>Use an authorized administrator account. Access is verified by the server.</p><form onSubmit={submit}><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label><label>Password<input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button auth-submit" disabled={loading}>{loading ? "Verifying…" : "Admin sign in ↗"}</button></form><p className="auth-switch"><Link to="/login">Return to user sign in</Link></p></section></main>;
}
