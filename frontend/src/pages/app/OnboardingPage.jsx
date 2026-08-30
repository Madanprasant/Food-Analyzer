import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiRequest } from "../../lib/api";

const allergyOptions = ["Dairy", "Eggs", "Gluten", "Peanuts", "Tree nuts", "Soy", "Shellfish"];
const avoidOptions = ["Beef", "Eggs", "Fish", "Meat", "Pork", "Seafood"];
const initialProfile = {
  display_name: "", age: "", height_cm: "", weight_kg: "", sex_for_estimation: "prefer_not_to_say",
  activity_level: "moderately_active", fitness_goal: "general_healthy_eating", diet_preference: "vegetarian",
  target_source: "suggested", calorie_target: "", protein_target_g: "", allergies: [], disliked_foods: [], preferred_foods: "",
};

function ChoiceChips({ options, values, onChange, disabled }) {
  function toggle(option) { onChange(values.includes(option) ? values.filter((value) => value !== option) : [...values, option]); }
  return <div className="choice-chips">{options.map((option) => <button className={values.includes(option) ? "chip selected" : "chip"} type="button" disabled={disabled} onClick={() => toggle(option)} key={option}>{option}</button>)}</div>;
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const savedUser = JSON.parse(localStorage.getItem("platesignal_user") || "{}");
  const [form, setForm] = useState({ ...initialProfile, display_name: savedUser.profile?.display_name || "" });
  const [noKnownAllergies, setNoKnownAllergies] = useState(true);
  const [noFoodsToAvoid, setNoFoodsToAvoid] = useState(true);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const update = (name, value) => setForm((current) => ({ ...current, [name]: value }));

  async function handleSubmit(event) {
    event.preventDefault(); setError(""); setIsSubmitting(true);
    try {
      const payload = {
        ...form, age: Number(form.age), height_cm: Number(form.height_cm), weight_kg: Number(form.weight_kg),
        calorie_target: form.target_source === "custom" ? Number(form.calorie_target) : null,
        protein_target_g: form.target_source === "custom" && form.protein_target_g ? Number(form.protein_target_g) : null,
        allergies: noKnownAllergies ? [] : form.allergies, disliked_foods: noFoodsToAvoid ? [] : form.disliked_foods,
        preferred_foods: form.preferred_foods.split(",").map((item) => item.trim()).filter(Boolean), nutrition_goals: [],
      };
      const user = await apiRequest("/users/me/onboarding", { method: "POST", body: JSON.stringify(payload) });
      localStorage.setItem("platesignal_user", JSON.stringify(user)); navigate("/dashboard");
    } catch (requestError) { setError(requestError.message); } finally { setIsSubmitting(false); }
  }

  return <main className="onboarding-shell"><section className="onboarding-intro"><div className="wordmark"><span className="wordmark-mark">⌁</span> PLATESIGNAL</div><div><div className="terminal-label">PROFILE CALIBRATION / 01</div><h1>Set a helpful starting point, not a perfect number.</h1><p>We use your profile to suggest targets. They are adjustable starting estimates, not medical advice.</p></div></section>
    <form className="onboarding-form" onSubmit={handleSubmit}>
      <fieldset><legend>About you</legend><label>Display name<input required value={form.display_name} onChange={(event) => update("display_name", event.target.value)} /></label><div className="two-fields"><label>Age<input required type="number" min="13" max="120" value={form.age} onChange={(event) => update("age", event.target.value)} /></label><label>Height (cm)<input required type="number" min="50" value={form.height_cm} onChange={(event) => update("height_cm", event.target.value)} /></label></div><label>Weight (kg)<input required type="number" min="15" value={form.weight_kg} onChange={(event) => update("weight_kg", event.target.value)} /></label><label>For energy estimate only<select value={form.sex_for_estimation} onChange={(event) => update("sex_for_estimation", event.target.value)}><option value="prefer_not_to_say">Prefer not to say — use a neutral estimate</option><option value="female">Female</option><option value="male">Male</option></select></label></fieldset>
      <fieldset><legend>Goals & eating pattern</legend><label>Daily activity<select value={form.activity_level} onChange={(event) => update("activity_level", event.target.value)}><option value="sedentary">Mostly sitting</option><option value="lightly_active">Light activity most days</option><option value="moderately_active">Regular exercise (3–5 days/week)</option><option value="very_active">Intense training or physical work</option></select></label><label>Main goal<select value={form.fitness_goal} onChange={(event) => update("fitness_goal", event.target.value)}><option value="weight_loss">Lose weight gradually</option><option value="weight_maintenance">Maintain my weight</option><option value="muscle_gain">Gain muscle</option><option value="general_healthy_eating">Eat healthier overall</option></select></label><label>Eating preference<select value={form.diet_preference} onChange={(event) => update("diet_preference", event.target.value)}><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option><option value="non_vegetarian">Non-vegetarian</option><option value="other">Other</option></select></label></fieldset>
      <fieldset><legend>Your daily targets</legend><div className="target-choice"><label className={form.target_source === "suggested" ? "radio-card chosen" : "radio-card"}><input type="radio" name="target-source" value="suggested" checked={form.target_source === "suggested"} onChange={(event) => update("target_source", event.target.value)} /><span><strong>Suggest my starting targets</strong><small>We calculate calories and protein from your profile and goal. You can edit them later.</small></span></label><label className={form.target_source === "custom" ? "radio-card chosen" : "radio-card"}><input type="radio" name="target-source" value="custom" checked={form.target_source === "custom"} onChange={(event) => update("target_source", event.target.value)} /><span><strong>I already have my own targets</strong><small>Use this only when you have a target from a professional, coach, or existing plan.</small></span></label></div>{form.target_source === "custom" && <div className="two-fields"><label>Daily calories<input required type="number" min="800" value={form.calorie_target} onChange={(event) => update("calorie_target", event.target.value)} /></label><label>Protein (g/day)<input type="number" min="0" value={form.protein_target_g} onChange={(event) => update("protein_target_g", event.target.value)} /></label></div>}</fieldset>
      <fieldset><legend>Food considerations</legend><label className="toggle-row"><input type="checkbox" checked={noKnownAllergies} onChange={(event) => { setNoKnownAllergies(event.target.checked); if (event.target.checked) update("allergies", []); }} /><span><strong>No known allergies or intolerances</strong><small>You can change this at any time.</small></span></label>{!noKnownAllergies && <><p className="field-hint">Select any that apply.</p><ChoiceChips options={allergyOptions} values={form.allergies} onChange={(values) => update("allergies", values)} /></>}<label className="toggle-row"><input type="checkbox" checked={noFoodsToAvoid} onChange={(event) => { setNoFoodsToAvoid(event.target.checked); if (event.target.checked) update("disliked_foods", []); }} /><span><strong>No foods to avoid</strong><small>We will not filter recommendations.</small></span></label>{!noFoodsToAvoid && <><p className="field-hint">Select any that you avoid.</p><ChoiceChips options={avoidOptions} values={form.disliked_foods} onChange={(values) => update("disliked_foods", values)} /></>}<label>Foods you enjoy <small>Optional — comma-separated</small><input value={form.preferred_foods} placeholder="e.g. dal, curd, paneer" onChange={(event) => update("preferred_foods", event.target.value)} /></label></fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}<button className="button onboarding-submit" disabled={isSubmitting} type="submit">{isSubmitting ? "Saving profile…" : "Save profile and continue ↗"}</button>
    </form>
  </main>;
}
