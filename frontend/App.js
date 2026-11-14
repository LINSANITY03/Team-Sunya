import { useState } from "react";
import SimulationSetup from "./SimulationSetup.jsx";
import "./Dashboard.css";

const plans = [
  ["Example current plan", "Maize", "Maize", "Maize"],
  ["Alternative A", "Maize", "Cowpea", "Maize"],
  ["Alternative B", "Sorghum", "Cowpea", "Maize"],
];

export default function App() {
  const [screen, setScreen] = useState("map");
  const [settings, setSettings] = useState(null);

  function showCropPlans(selectedSettings) {
    setSettings(selectedSettings);
    setScreen("results");
  }

  if (screen === "setup") {
    return <SimulationSetup onStart={showCropPlans} />;
  }

  const highlightedPlan =
    settings?.priority === "Save water" ? "Alternative B" : "Alternative A";

  return (
    <section className="nepal-dashboard">
      <header className="nepal-header">▲ Field Shift Nepal</header>

      <div className="nepal-layout">
        <nav className="nepal-nav" aria-label="Dashboard">
          <button onClick={() => setScreen("map")}>Map</button>
          <button onClick={() => setScreen("setup")}>Farm setup</button>
          <button disabled={!settings} onClick={() => setScreen("results")}>
            Crop plans
          </button>
        </nav>

        <main className="nepal-content">
          {screen === "map" ? (
            <>
              <p className="nepal-banner">Select a farming area on the map</p>
              <div className="nepal-map">
              <iframe
              src="/project-nepal.html?v=2"
              title="Interactive Nepal district map"
              style={{ width: "100%", height: "680px", border: 0 }}
              />
              </div>
            </>
          ) : (
            <>
              <h1>Compare crop plans</h1>
              <p className="nepal-banner">
                Melamchi, Sindhupalchok · {settings.priority}
              </p>
              <p>Demo crop sequences for comparison.</p>

              <div className="nepal-table">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Plan</th>
                      <th scope="col">Season 1</th>
                      <th scope="col">Season 2</th>
                      <th scope="col">Season 3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map(([name, first, second, third]) => (
                      <tr
                        key={name}
                        className={name === highlightedPlan ? "nepal-highlight" : ""}
                      >
                        <th scope="row">{name}</th>
                        <td>{first}</td>
                        <td>{second}</td>
                        <td>{third}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p>Highlighted for your selected priority: <strong>{highlightedPlan}</strong></p>
            </>
          )}
        </main>
      </div>
    </section>
  );
}