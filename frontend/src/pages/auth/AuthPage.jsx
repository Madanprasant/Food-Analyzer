import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, saveSession } from "../../lib/api";
import { isFirebaseConfigured, signInWithGoogle } from "../../lib/firebase";

export default function AuthPage({ mode }) {
  const isSignup = mode === "signup";
  const navigate = useNavigate();
  const [form, setForm] = useState({ display_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const payload = isSignup ? form : { email: form.email, password: form.password };
      const session = await apiRequest(`/auth/${isSignup ? "signup" : "login"}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      saveSession(session);
      navigate(session.user.is_onboarded ? "/dashboard" : "/onboarding");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGoogleSignIn() {
    setError("");
    setIsSubmitting(true);
    try {
      const idToken = await signInWithGoogle();
      const session = await apiRequest("/auth/firebase", { method: "POST", body: JSON.stringify({ id_token: idToken }) });
      saveSession(session);
      navigate(session.user.is_onboarded ? "/dashboard" : "/onboarding");
    } catch (requestError) {
      setError(requestError.message || "Google Sign-In could not be completed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <Link className="wordmark" to="/"><span className="wordmark-mark" aria-hidden="true">⌁</span> PLATESIGNAL</Link>
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="terminal-label">{isSignup ? "CREATE ACCOUNT" : "WELCOME BACK"}</div>
        <h1 id="auth-title">{isSignup ? "Build a clearer picture of your plate." : "Pick up where your plate left off."}</h1>
        <p>{isSignup ? "Your profile lets every recommendation reflect your actual goals." : "Sign in to continue tracking your confirmed meals."}</p>
        <form onSubmit={handleSubmit} noValidate>
          {isSignup && <label>Display name<input required name="display_name" value={form.display_name} onChange={(event) => update("display_name", event.target.value)} autoComplete="name" /></label>}
          <label>Email<input required type="email" name="email" value={form.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" /></label>
          <label>Password<input required type="password" name="password" minLength="8" value={form.password} onChange={(event) => update("password", event.target.value)} autoComplete={isSignup ? "new-password" : "current-password"} /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button auth-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? "Working…" : isSignup ? "Create account ↗" : "Sign in ↗"}</button>
        </form>
        <div className="auth-divider"><span>or continue with</span></div>
        <button className="google-button" type="button" onClick={handleGoogleSignIn} disabled={isSubmitting}>
          <span className="google-mark" aria-hidden="true">G</span> Continue with Google
        </button>
        {!isFirebaseConfigured && <p className="firebase-note">Google Sign-In is ready to connect. Add the Firebase settings in <code>frontend/.env</code>.</p>}
        <p className="auth-switch">{isSignup ? "Already have an account?" : "New to PlateSignal?"} <Link to={isSignup ? "/login" : "/signup"}>{isSignup ? "Sign in" : "Create one"}</Link></p>
      </section>
    </main>
  );
}
