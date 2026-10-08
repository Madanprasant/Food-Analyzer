import { Fragment, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiRequest } from "../../lib/api";
import { AppNav } from "./AnalyzeFoodPage";

const nutrientPattern = /\b(calories?|protein|carbohydrates?|carbs?|fat|fiber)\s*:\s*([\d,.]+)\s*(kcal|g)?/gi;

function inlineText(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => part.startsWith("**") && part.endsWith("**")
    ? <strong key={index}>{part.slice(2, -2)}</strong>
    : <Fragment key={index}>{part}</Fragment>);
}

function nutritionStats(text) {
  const seen = new Set();
  const stats = [];
  for (const match of text.matchAll(nutrientPattern)) {
    const label = match[1].toLowerCase().replace("carbs", "carbohydrates").replace(/s$/, "");
    if (!seen.has(label)) { seen.add(label); stats.push({ label, value: `${match[2]} ${match[3] || ""}`.trim() }); }
  }
  return stats;
}

function isHistoryLine(text) {
  return /\d{4}-\d{2}-\d{2}|\b(?:today|yesterday)\b|\b\d[\d,.]*\s*kcal\b/i.test(text);
}

function AssistantContent({ text }) {
  const stats = nutritionStats(text);
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) { index += 1; continue; }
    const heading = line.match(/^#{1,3}\s+(.+)$/) || (line.match(/^\*\*(.+)\*\*$/) ? [null, line.slice(2, -2)] : null);
    if (heading) { blocks.push(<h3 key={`heading-${index}`}>{heading[1]}</h3>); index += 1; continue; }
    const bullet = line.match(/^[-*•]\s+(.+)$/);
    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      const items = [];
      while (index < lines.length) {
        const item = lines[index].trim().match(ordered ? /^\d+[.)]\s+(.+)$/ : /^[-*•]\s+(.+)$/);
        if (!item) break;
        items.push(item[1]); index += 1;
      }
      const List = ordered ? "ol" : "ul";
      blocks.push(<List className={`assistant-list ${items.some(isHistoryLine) ? "food-history-list" : ""}`} key={`list-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inlineText(item)}</li>)}</List>);
      continue;
    }
    const paragraph = [line]; index += 1;
    while (index < lines.length && lines[index].trim() && !/^#{1,3}\s+|^[-*•]\s+|^\d+[.)]\s+/.test(lines[index].trim())) { paragraph.push(lines[index].trim()); index += 1; }
    blocks.push(<p key={`paragraph-${index}`}>{inlineText(paragraph.join(" "))}</p>);
  }
  return <div className="assistant-content">{stats.length >= 2 && <div className="nutrition-stats" aria-label="Nutrition highlights">{stats.map((stat) => <div key={stat.label}><span>{stat.label}</span><strong>{stat.value}</strong></div>)}</div>}{blocks}</div>;
}

function RecommendationCards({ sources = [] }) {
  const recommendations = sources.filter((source) => source.type === "recommendation");
  if (!recommendations.length) return null;
  return <section className="assistant-recommendations" aria-label="Recommendations used"><span>Recommendations considered</span><div>{recommendations.map((source) => <article key={source.title}><strong>RECOMMENDATION</strong><p>{source.title}</p></article>)}</div></section>;
}

function SourceList({ sources = [] }) {
  const visibleSources = sources.filter((source) => source.type !== "recommendation");
  if (!visibleSources.length) return null;
  return <section className="assistant-sources"><span>Based on</span><div>{visibleSources.map((source) => <small key={`${source.type}-${source.title}`}>{source.title}</small>)}</div></section>;
}

export default function ChatPage() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("platesignal_user") || "null");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  if (!user) { navigate("/login"); return null; }

  async function send(event) {
    event.preventDefault();
    const text = message.trim();
    if (!text || loading) return;
    setError(""); setMessage(""); setMessages((current) => [...current, { role: "user", text }]); setLoading(true);
    try {
      const response = await apiRequest("/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      setMessages((current) => [...current, { role: "assistant", text: response.answer, sources: response.sources }]);
    } catch (requestError) { setError(requestError.message); setMessage(text); } finally { setLoading(false); }
  }

  return <main className="app-shell"><AppNav /><section className="chat-page"><div className="chat-heading"><div><div className="terminal-label">FOOD & NUTRITION ASSISTANT</div><h1>Ask about your meals.</h1><p>Use your confirmed food history and sourced nutrition information. This assistant does not provide medical advice.</p></div><button className="text-button" type="button" onClick={() => { setMessages([]); setError(""); }} disabled={!messages.length}>Clear conversation</button></div><section className="chat-card"><div className="chat-messages" aria-live="polite">{messages.length === 0 && <div className="chat-empty"><strong>Try a food question</strong><p>“What did I eat today?” or “How much protein have I logged recently?”</p></div>}{messages.map((item, index) => <article className={`chat-message ${item.role}`} key={`${item.role}-${index}`}><header><span className="chat-avatar" aria-hidden="true">{item.role === "user" ? "Y" : "⌁"}</span><strong>{item.role === "user" ? "You" : "PLATESIGNAL"}</strong></header>{item.role === "assistant" ? <><AssistantContent text={item.text} /><RecommendationCards sources={item.sources} /><SourceList sources={item.sources} /></> : <p>{item.text}</p>}</article>)}{loading && <article className="chat-message assistant chat-loading"><header><span className="chat-avatar" aria-hidden="true">⌁</span><strong>PLATESIGNAL</strong></header><p>Reviewing your food context…</p></article>}</div><form className="chat-form" onSubmit={send}><label>Ask a food or nutrition question<textarea value={message} onChange={(event) => setMessage(event.target.value)} maxLength="1000" placeholder="e.g. What nutrients did I get from today’s meals?" disabled={loading} /></label><button className="button" type="submit" disabled={!message.trim() || loading}>{loading ? "Thinking…" : "Send ↗"}</button></form>{error && <p className="form-error" role="alert">{error}</p>}</section></section></main>;
}
