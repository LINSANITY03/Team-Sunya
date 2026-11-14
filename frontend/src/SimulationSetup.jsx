import { useState } from "react";
import "./SimulationSetup.css";

const fields = [
  {
    name: "soil",
    label: "Soil type",
    options: ["I'm not sure", "Loamy", "Clay", "Sandy"],
  },
  {
    name: "irrigation",
    label: "Irrigation access",
    options: ["Limited irrigation", "Rain-fed only", "Regular irrigation"],
  },
  {
    name: "priority",
    label: "Main priority",
    options: ["Save water", "Improve soil health"],
  },
];

export default function SimulationSetup({ point, onStart, onBack }) {
  const [config, setConfig] = useState({
    soil: fields[0].options[0],
    irrigation: fields[1].options[0],
    priority: fields[2].options[0],
  });
  const [submitted, setSubmitted] = useState(null);

  function startSimulation(event) {
    event.preventDefault();
    const settings = { ...config, ...point, location: point.district };
    setSubmitted(settings);
    onStart?.(settings);
  }

  return (
    <section className="fs-dashboard" aria-label="Field Shift Nepal">
      <header className="fs-header">
        <span aria-hidden="true">▲</span> Field Shift Nepal
      </header>
      <div className="fs-layout">
        <aside className="fs-sidebar">
          <span>Farm setup</span>
        </aside>
        <main className="fs-content">
          <button type="button" onClick={onBack}>
            ← Back to map
          </button>
          <div className="fs-location">
            Nepal / {point.district} · {point.latitude.toFixed(5)},{" "}
            {point.longitude.toFixed(5)}
          </div>
          <h1>Set up your simulation</h1>
          <form onSubmit={startSimulation}>
            {fields.map(({ name, label, options }, index) => (
              <label className="fs-row" key={name}>
                <span className="fs-number" aria-hidden="true">
                  {index + 1}
                </span>
                <span className="fs-field">
                  {label}
                  <select
                    value={config[name]}
                    onChange={(event) =>
                      setConfig({ ...config, [name]: event.target.value })
                    }
                  >
                    {options.map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                </span>
              </label>
            ))}
            <button className="fs-start" type="submit">
              <span aria-hidden="true">▶</span> Start Simulation
            </button>
          </form>
          <div role="status">
            {submitted && (
              <div className="fs-summary">
                <strong>
                  {onStart
                    ? "Configuration submitted"
                    : "Simulation settings captured · Demo"}
                </strong>
                <dl>
                  {fields.map(({ name, label }) => (
                    <div key={name}>
                      <dt>{label}</dt>
                      <dd>{submitted[name]}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
        </main>
      </div>
    </section>
  );
}
