const API_BASE = "";

/** Update the percentage hint badge next to a range slider */
function updateHint(inputId, hintId) {
  const value = parseFloat(document.getElementById(inputId).value);
  document.getElementById(hintId).textContent = `${Math.round(value * 100)}%`;
}

/** Show / hide UI sections */
function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

/** Render the prediction response into the result panel */
function renderResult(data) {
  document.getElementById("crimeName").textContent = data.predicted_crime;
  document.getElementById("confidence").textContent = `${data.confidence}% confidence`;

  const list = document.getElementById("topList");
  list.innerHTML = "";
  data.top_predictions.forEach((p) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="bar-label">${p.crime_type}</span>
      <span class="bar-track">
        <span class="bar-fill" style="width:${p.probability}%"></span>
      </span>
      <span class="bar-pct">${p.probability}%</span>
    `;
    list.appendChild(li);
  });

  show("result");
}

/** Main form submit handler */
document.getElementById("predictionForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  hide("result");
  hide("errorBox");

  const btn = document.getElementById("submitBtn");
  btn.disabled = true;
  btn.textContent = "Predicting…";

  const form = e.target;
  const payload = {
    hour:               parseInt(form.hour.value, 10),
    day_of_week:        parseInt(form.day_of_week.value, 10),
    month:              parseInt(form.month.value, 10),
    district:           form.district.value,
    population_density: parseFloat(form.population_density.value),
    poverty_rate:       parseFloat(form.poverty_rate.value),
    unemployment_rate:  parseFloat(form.unemployment_rate.value),
    police_presence:    parseFloat(form.police_presence.value),
  };

  try {
    const res = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || `Server error ${res.status}`);
    }

    renderResult(data);
  } catch (err) {
    const box = document.getElementById("errorBox");
    box.textContent = `Error: ${err.message}`;
    show("errorBox");
  } finally {
    btn.disabled = false;
    btn.textContent = "Predict Crime Risk";
  }
});
