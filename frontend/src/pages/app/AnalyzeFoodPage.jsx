import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../../lib/api";

const servingOptions = [
  { value: 0.75, label: "Small", description: "about ¾ serving" },
  { value: 1, label: "Regular", description: "reference serving" },
  { value: 1.5, label: "Large", description: "about 1½ servings" },
];

export default function AnalyzeFoodPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [classes, setClasses] = useState([]);
  const [selectedFood, setSelectedFood] = useState("");
  const [query, setQuery] = useState("");
  const [serving, setServing] = useState(1);
  const [servingGrams, setServingGrams] = useState("");
  const [nutritionInfo, setNutritionInfo] = useState(null);
  const [savedMeal, setSavedMeal] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => {
    if (!selectedFood) { setNutritionInfo(null); return; }
    apiRequest(`/nutrition/${encodeURIComponent(selectedFood)}`).then(setNutritionInfo).catch(() => setNutritionInfo(null));
  }, [selectedFood]);
  const matchingClasses = useMemo(() => classes.filter((item) => item.includes(query.toLowerCase())).slice(0, 12), [classes, query]);

  function selectFile(event) {
    const nextFile = event.target.files?.[0];
    if (!nextFile) return;
    if (!nextFile.type.match(/^image\/(jpeg|png|webp)$/)) { setError("Choose a JPEG, PNG, or WebP image."); return; }
    if (nextFile.size > 5 * 1024 * 1024) { setError("Choose an image smaller than 5 MB."); return; }
    if (preview) URL.revokeObjectURL(preview);
    setFile(nextFile); setPreview(URL.createObjectURL(nextFile)); setResult(null); setError(""); setStatus("idle");
  }

  async function analyze() {
    if (!file) { setError("Choose a food image first."); return; }
    setStatus("analyzing"); setError("");
    try {
      const formData = new FormData(); formData.append("image", file);
      const response = await apiRequest("/food/analyze", { method: "POST", body: formData });
      setResult(response); setSelectedFood(response.predicted_food); setStatus("result");
      const classData = await apiRequest("/food/classes"); setClasses(classData.classes);
    } catch (requestError) { setError(requestError.message); setStatus("idle"); }
  }

  async function confirm() {
    if (!result || !selectedFood) return;
    setStatus("saving"); setError("");
    try {
      if (nutritionInfo?.status === "verified" && !servingGrams) {
        setError("Enter the amount in grams so we can calculate nutrition from the per‑100g IFCT record."); setStatus("result"); return;
      }
      const confirmed = await apiRequest("/food/confirm", { method: "POST", body: JSON.stringify({ analysis_id: result.analysis_id, final_food: selectedFood, serving_multiplier: serving, serving_grams: servingGrams ? Number(servingGrams) : null }) });
      setSavedMeal(confirmed);
      setStatus("saved");
    } catch (requestError) { setError(requestError.message); setStatus("result"); }
  }

  if (status === "saved") return <main className="app-shell"><AppNav /><section className="completion-card"><div className="terminal-label">MEAL SAVED</div><h1>{selectedFood}</h1>{savedMeal?.nutrition_snapshot ? <><p>Nutrition was calculated from the sourced IFCT per‑100g record for your selected amount.</p><div className="saved-nutrition"><span><strong>{savedMeal.nutrition_snapshot.calories_kcal}</strong> kcal</span><span><strong>{savedMeal.nutrition_snapshot.protein_g}</strong> g protein</span><span><strong>{savedMeal.nutrition_snapshot.carbohydrate_g}</strong> g carbs</span><span><strong>{savedMeal.nutrition_snapshot.fat_g}</strong> g fat</span></div></> : <p>Nutrition is pending because this food does not yet have a traceable prepared-food record in the database.</p>}<div className="completion-actions"><Link className="button" to="/analyze">Analyze another meal ↗</Link><Link className="text-link" to="/dashboard">Back to dashboard</Link></div></section></main>;

  return <main className="app-shell"><AppNav /><section className="analysis-layout"><div className="analysis-heading"><div className="terminal-label">IMAGE ANALYSIS / EFFICIENTNETV2-S</div><h1>Read the signal from your plate.</h1><p>Use a clear photo of one meal. You always confirm the prediction before it is saved.</p></div><div className="analysis-grid"><section className="upload-card"><label className={preview ? "image-drop has-preview" : "image-drop"}><input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={selectFile} /><span className="upload-placeholder">{preview ? <img src={preview} alt="Selected food" /> : <><b aria-hidden="true">＋</b><strong>Add a food photo</strong><small>JPEG, PNG, or WebP · up to 5 MB</small></>}</span></label>{preview && <button className="change-image" type="button" onClick={() => { setFile(null); URL.revokeObjectURL(preview); setPreview(""); setResult(null); }}>Choose a different image</button>}<button className="button analyze-button" disabled={!file || status === "analyzing"} onClick={analyze}>{status === "analyzing" ? "Analyzing image…" : "Analyze this meal ↗"}</button></section>{result && <section className="result-card"><div className="terminal-label">MODEL RESULT</div>{result.low_confidence && <p className="low-confidence" role="status">Low confidence—please verify the result.</p>}<h2>{result.predicted_food}</h2><div className="confidence"><span>Confidence</span><strong>{(result.confidence * 100).toFixed(1)}%</strong></div><div className="confidence-bar"><span style={{ width: `${result.confidence * 100}%` }} /></div><h3>Top predictions</h3><div className="predictions">{result.top_k.map((prediction) => <button className={selectedFood === prediction.food ? "prediction selected" : "prediction"} type="button" onClick={() => setSelectedFood(prediction.food)} key={prediction.food}><span>{prediction.food}</span><strong>{(prediction.confidence * 100).toFixed(1)}%</strong></button>)}</div><label className="correction-search">Not listed? Search all 239 foods<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a food name" /></label>{query && <div className="search-results">{matchingClasses.map((item) => <button type="button" onClick={() => { setSelectedFood(item); setQuery(""); }} key={item}>{item}</button>)}</div>}<h3>Serving size</h3>{nutritionInfo?.status === "verified" ? <><p className="source-note">Verified IFCT record · values are per 100 g. Enter your meal amount to calculate it.</p><label className="gram-input">Amount eaten (grams)<input required type="number" min="1" max="3000" value={servingGrams} onChange={(event) => setServingGrams(event.target.value)} placeholder="e.g. 120" /></label></> : <><div className="serving-options">{servingOptions.map((option) => <button className={serving === option.value ? "serving selected" : "serving"} type="button" onClick={() => setServing(option.value)} key={option.label}><strong>{option.label}</strong><small>{option.description}</small></button>)}</div><p className="pending-note">Nutrition information is pending for this food. The meal will be saved without invented values.</p></>}<button className="button confirm-button" onClick={confirm} disabled={status === "saving"}>{status === "saving" ? "Saving meal…" : `Confirm ${selectedFood} ↗`}</button></section>}</div>{error && <p className="form-error analysis-error" role="alert">{error}</p>}</section></main>;
}

export function AppNav() {
  return <nav className="app-nav"><Link className="wordmark" to="/dashboard"><span className="wordmark-mark">⌁</span> PLATESIGNAL</Link><div><Link to="/dashboard">Dashboard</Link><Link className="nav-active" to="/analyze">Analyze food</Link><button type="button" onClick={() => { localStorage.removeItem("platesignal_access_token"); localStorage.removeItem("platesignal_user"); window.location.assign("/"); }}>Log out</button></div></nav>;
}
