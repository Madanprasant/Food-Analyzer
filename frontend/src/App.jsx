import { Link, Route, Routes } from "react-router-dom";
import AuthPage from "./pages/auth/AuthPage";
import OnboardingPage from "./pages/app/OnboardingPage";
import AnalyzeFoodPage from "./pages/app/AnalyzeFoodPage";
import DashboardPage from "./pages/app/DashboardPage";

const Check = () => <span aria-hidden="true" className="check">✓</span>;

function LandingPage() {
  return (
    <main className="landing-shell">
      <nav className="nav" aria-label="Main navigation">
        <Link className="wordmark" to="/">
          <span className="wordmark-mark" aria-hidden="true">⌁</span>
          PLATESIGNAL
        </Link>
        <div className="nav-actions">
          <Link className="text-link" to="/login">Sign in</Link>
          <Link className="button button-small" to="/signup">Begin tracking</Link>
        </div>
      </nav>

      <section className="hero" aria-labelledby="hero-title">
        <div className="eyebrow"><span className="live-dot" /> MODEL CONNECTED · 239 FOOD CLASSES</div>
        <h1 id="hero-title">See what’s on your plate.<br /><em>Know what it means.</em></h1>
        <p className="hero-copy">
          Food recognition built for Indian cuisine, with nutrition context that adapts to your own goals.
        </p>
        <div className="hero-actions">
          <Link className="button" to="/signup">Create your profile <span aria-hidden="true">↗</span></Link>
          <a className="text-link discover" href="#how-it-works">Explore the system <span aria-hidden="true">↓</span></a>
        </div>
      </section>

      <section className="signal-grid" aria-label="System preview">
        <article className="signal-card feature-card">
          <div className="terminal-label">01 / VISION</div>
          <div className="food-window" aria-hidden="true">
            <div className="food-glow" />
            <div className="plate"><div className="meal"><i /><i /><i /><i /></div></div>
            <span className="scan scan-a" /><span className="scan scan-b" />
          </div>
          <div className="prediction-line"><span>masala dosa</span><strong>94.2%</strong></div>
          <div className="meter"><span /></div>
        </article>
        <article className="signal-card stats-card readiness-card">
          <div className="terminal-label">02 / YOUR DAILY SIGNAL</div>
          <div className="ready-mark" aria-hidden="true">⌁</div>
          <h3>Set your targets once.</h3>
          <p>See only your confirmed meals, not made-up numbers.</p>
        </article>
        <article className="signal-card insight-card">
          <div className="terminal-label">03 / PERSONALIZATION</div>
          <p className="insight">Your <mark>goals, preferences</mark> and meal history shape every insight.</p>
          <div className="status-row"><Check /> Starts after profile calibration</div>
        </article>
      </section>

      <section id="how-it-works" className="workflow">
        <div><div className="terminal-label">HOW IT WORKS</div><h2>From image to an informed next choice.</h2></div>
        <ol>
          <li><span>01</span><div><h3>Capture</h3><p>Upload a meal image and review the model’s top predictions.</p></div></li>
          <li><span>02</span><div><h3>Confirm</h3><p>Correct the food when needed—your final choice drives the analysis.</p></div></li>
          <li><span>03</span><div><h3>Understand</h3><p>Track confirmed meals against your own nutrition targets.</p></div></li>
        </ol>
      </section>

      <footer><span>PLATESIGNAL / NUTRITION INTELLIGENCE</span><span>BUILT FOR INDIAN FOOD</span></footer>
    </main>
  );
}

function PlaceholderPage({ title }) {
  return <main className="placeholder"><Link className="wordmark" to="/">⌁ PLATESIGNAL</Link><h1>{title}</h1><p>This route is being implemented in the next phase.</p></main>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/analyze" element={<AnalyzeFoodPage />} />
      <Route path="*" element={<PlaceholderPage title="Page not found" />} />
    </Routes>
  );
}
