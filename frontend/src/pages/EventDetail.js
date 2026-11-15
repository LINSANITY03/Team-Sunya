import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getRotation } from "../api";

const METRICS = [
  ["soil_fit", "Soil fit"], ["water_fit", "Water fit"], ["timing", "Timing"],
  ["rotation_health", "Rotation health"], ["ndvi_support", "NDVI support"],
  ["profit", "Profit"], ["food", "Food"],
];

export default function EventDetail() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getRotation(id).then(setD).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="pad err-text">{error}</p>;
  if (!d) return <p className="pad">Loading…</p>;

  return (
    <div className="pad">
      <Link to="/events">← Back to events</Link>
      <h2>Recommendation</h2>
      <div className="mono">{d.recommendation_id}</div>
      <p className="muted">
        {d.status} · {d.location.latitude}, {d.location.longitude} · updated{" "}
        {new Date(d.updated_at).toLocaleString()}
      </p>

      <div className="chips">
        {Object.entries(d.data_sources || {}).map(([name, s]) => (
          <span key={name} className={"badge " + (s.status === "SUCCESS" ? "ok" : "fail")}>
            {name}: {s.status}
          </span>
        ))}
      </div>

      {(d.results || []).map((r) => {
        const rd = r.rotation_data;
        return (
          <section key={r.rank} className="card">
            <h3>#{r.rank} {r.sequence}
              <span className="score">{(r.score * 100).toFixed(1)}%</span>
            </h3>
            <p className="muted">{rd.total_days} total days · {rd.fallow_days} fallow days</p>
            {rd.warnings && <p className="err-text">⚠ {rd.warnings}</p>}

            {METRICS.map(([k, label]) => (
              <div key={k} className="metric">
                <span>{label}</span>
                <div className="bar"><div style={{ width: `${(rd[k] || 0) * 100}%` }} /></div>
                <span>{(rd[k] ?? 0).toFixed(2)}</span>
              </div>
            ))}

            <div className="scroll-x">
              <table>
                <thead>
                  <tr><th>Crop</th><th>Sow</th><th>Harvest</th><th>Fallow (d)</th>
                      <th>Water ratio</th><th>Demand (mm)</th><th>NDVI</th></tr>
                </thead>
                <tbody>
                  {rd.events.map((e, i) => (
                    <tr key={i}>
                      <td>{e.crop}</td><td>{e.sow}</td><td>{e.harvest}</td>
                      <td>{e.fallow_d}</td><td>{e.water_ratio.toFixed(2)}</td>
                      <td>{Math.round(e.demand_mm)}</td><td>{e.ndvi.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}

      <p className="muted small">
        Data: NASA POWER, MODIS, SoilGrids, elevation data. Map © OpenStreetMap contributors.
      </p>
    </div>
  );
}