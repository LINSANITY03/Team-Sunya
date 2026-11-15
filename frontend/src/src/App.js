import React, { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./styles.css";

const API_BASE = "";
const EXAMPLE = { latitude: 27.676546, longitude: 84.463889 };

const NEPAL = [
  [27.876542, 88.120441],
  [27.445819, 88.043133],
  [26.810405, 88.174804],
  [26.414615, 88.060238],
  [26.397898, 87.227472],
  [26.630985, 86.024393],
  [26.726198, 85.251779],
  [27.234901, 84.675018],
  [27.364506, 83.304249],
  [27.925479, 81.999987],
  [28.416095, 81.057203],
  [28.79447, 80.088425],
  [29.729865, 80.476721],
  [30.183481, 81.111256],
  [30.422717, 81.525804],
  [30.115268, 82.327513],
  [29.463732, 83.337115],
  [29.320226, 83.898993],
  [28.839894, 84.23458],
  [28.642774, 85.011638],
  [28.203576, 85.82332],
  [27.974262, 86.954517],
];

const DEMO_ROTATIONS = [
  {
    rank: 1,
    sequence: "Rice > Mungbean > Mustard",
    score: 0.771,
    rotation_data: {
      total_days: 303,
      fallow_days: 13,
      soil_fit: 0.97,
      water_fit: 0.42,
      profit: 1,
      food: 0.67,
      timing: 0.89,
      rotation_health: 0.8,
      ndvi_support: 0.86,
      events: [
        {
          crop: "Rice",
          sow: "2026-03-01",
          harvest: "2026-06-29",
          fallow_d: 0,
          water_ratio: 0.21,
          demand_mm: 2155,
          ndvi: 0.66,
        },
        {
          crop: "Mungbean",
          sow: "2026-07-09",
          harvest: "2026-09-22",
          fallow_d: 0,
          water_ratio: 0.84,
          demand_mm: 932,
          ndvi: 0.87,
        },
        {
          crop: "Mustard",
          sow: "2026-10-15",
          harvest: "2026-12-29",
          fallow_d: 13,
          water_ratio: 0.2,
          demand_mm: 716,
          ndvi: 0.77,
        },
      ],
    },
  },
  {
    rank: 2,
    sequence: "Maize > Cowpea > Wheat",
    score: 0.746,
    rotation_data: {
      total_days: 284,
      fallow_days: 10,
      soil_fit: 0.82,
      water_fit: 0.66,
      profit: 0.71,
      food: 0.91,
      timing: 0.83,
      rotation_health: 0.79,
      ndvi_support: 0.74,
      events: [
        {
          crop: "Maize",
          sow: "2026-03-01",
          harvest: "2026-06-10",
          fallow_d: 0,
          water_ratio: 0.53,
          demand_mm: 640,
          ndvi: 0.73,
        },
        {
          crop: "Cowpea",
          sow: "2026-06-16",
          harvest: "2026-08-30",
          fallow_d: 5,
          water_ratio: 0.74,
          demand_mm: 410,
          ndvi: 0.78,
        },
        {
          crop: "Wheat",
          sow: "2026-09-05",
          harvest: "2026-12-09",
          fallow_d: 5,
          water_ratio: 0.71,
          demand_mm: 520,
          ndvi: 0.71,
        },
      ],
    },
  },
  {
    rank: 3,
    sequence: "Millet > Lentil",
    score: 0.719,
    rotation_data: {
      total_days: 243,
      fallow_days: 8,
      soil_fit: 0.89,
      water_fit: 0.84,
      profit: 0.57,
      food: 0.76,
      timing: 0.76,
      rotation_health: 0.84,
      ndvi_support: 0.71,
      events: [
        {
          crop: "Millet",
          sow: "2026-06-01",
          harvest: "2026-09-28",
          fallow_d: 0,
          water_ratio: 0.86,
          demand_mm: 420,
          ndvi: 0.7,
        },
        {
          crop: "Lentil",
          sow: "2026-10-07",
          harvest: "2027-01-30",
          fallow_d: 8,
          water_ratio: 0.82,
          demand_mm: 325,
          ndvi: 0.72,
        },
      ],
    },
  },
];

const METRICS = [
  ["soil_fit", "Soil fit"],
  ["water_fit", "Water fit"],
  ["profit", "Profitability"],
  ["food", "Food security"],
];

const REPORT_METRICS = [
  ...METRICS.slice(0, 2),
  ["timing", "Timing"],
  ["rotation_health", "Rotation health"],
  ["ndvi_support", "NDVI support"],
  ...METRICS.slice(2),
];

const FINAL_STATUSES = ["COMPLETED", "FAILED", "PARTIAL_FAILED"];

function insideNepal(lat, lng) {
  let inside = false;
  for (let i = 0, j = NEPAL.length - 1; i < NEPAL.length; j = i++) {
    const [aLat, aLng] = NEPAL[i];
    const [bLat, bLng] = NEPAL[j];

    if (aLat > lat !== bLat > lat) {
      const edgeLng = aLng + ((bLng - aLng) * (lat - aLat)) / (bLat - aLat);
      if (lng < edgeLng) inside = !inside;
    }
  }
  return inside;
}

function WorldMap({ point, onPick }) {
  const container = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    const map = L.map(container.current, {
      scrollWheelZoom: false,
      zoomSnap: 0.25,

      minZoom: 0,
      maxZoom: 18,
      worldCopyJump: true,
      zoomControl: false,
    });

    mapRef.current = map;
    L.control.zoom({ position: "topright" }).addTo(map);
    map.fitBounds(NEPAL, { padding: [8, 8], animate: false }).zoomIn(0.25);

    const tiles = L.tileLayer(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }
    );
    tiles.on("tileerror", () => setTileError(true));
    tiles.on("tileload", () => setTileError(false));
    tiles.addTo(map);

    map.on("click", ({ latlng }) => {
      const selected = map.wrapLatLng(latlng);
      onPick(selected.lat, selected.lng);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [onPick]);

  useEffect(() => {
    const map = mapRef.current;
    const latLng = [point.latitude, point.longitude];

    if (!markerRef.current) {
      markerRef.current = L.circleMarker(latLng, {
        radius: 8,
        color: "#fff",
        weight: 3,
        fillColor: "#1e6747",
        fillOpacity: 1,
        interactive: false,
      }).addTo(map);
    } else {
      markerRef.current.setLatLng(latLng);
    }

    if (!map.getBounds().contains(latLng)) map.panTo(latLng);
  }, [point]);

  return (
    <>
      <div className="map-views">
        <button type="button" onClick={() => mapRef.current?.fitWorld()}>
          World view
        </button>
        <button
          type="button"
          onClick={() =>
            mapRef.current?.fitBounds(NEPAL, { padding: [16, 16] })
          }
        >
          Nepal view
        </button>
      </div>
      <div ref={container} className="nepal-map" aria-label="World map" />
      {tileError && <p className="map-note">Some map tiles could not load.</p>}
    </>
  );
}

async function request(path, options) {
  const response = await fetch(API_BASE.replace(/\/$/, "") + path, options);
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status}).`
    );
  }

  if (!data) throw new Error("The server returned an empty response.");
  return data;
}

function percent(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

function CropTable({ crops }) {
  const columns = [
    "Crop",
    "Sow",
    "Harvest",
    "Fallow (days)",
    "Water ratio",
    "Demand (mm)",
    "NDVI",
  ];

  return (
    <div className="table-wrap">
      <table aria-label="Crop schedule">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {crops.map((crop) => (
            <tr key={`${crop.crop}-${crop.sow}`}>
              <th scope="row">{crop.crop}</th>
              <td>{crop.sow}</td>
              <td>{crop.harvest}</td>
              <td>{crop.fallow_d ?? "—"}</td>
              <td>
                {Number.isFinite(crop.water_ratio)
                  ? crop.water_ratio.toFixed(2)
                  : "—"}
              </td>
              <td>{crop.demand_mm ?? "—"}</td>
              <td>{Number.isFinite(crop.ndvi) ? crop.ndvi.toFixed(2) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RotationCard({ rotation, report = false }) {
  const details = rotation.rotation_data || {};
  const crops = details.events || [];

  return (
    <article className={`panel rotation${report ? " report" : ""}`}>
      <div className="card-top">
        <span>Rank {rotation.rank}</span>
        <strong>{percent(rotation.score)} overall</strong>
      </div>

      <h3>{String(rotation.sequence ?? "").replaceAll(">", "→")}</h3>
      <p>
        {details.total_days ?? "—"} total days · {details.fallow_days ?? "—"}{" "}
        fallow days
      </p>

      {REPORT_METRICS.map(([key, label]) => (
        <div className="metric" key={key}>
          <span>{label}</span>
          <strong>{percent(details[key])}</strong>
          {Number.isFinite(details[key]) && (
            <meter min="0" max="1" value={details[key]} aria-label={label} />
          )}
        </div>
      ))}

      {details.warnings && <p className="error">{details.warnings}</p>}

      {crops.length > 0 &&
        (report ? (
          <CropTable crops={crops} />
        ) : (
          <details>
            <summary>Planting and harvest dates</summary>
            <CropTable crops={crops} />
          </details>
        ))}
    </article>
  );
}
function formatLocation(location) {
  return `${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`;
}

function Events({ runs }) {
  const [selected, setSelected] = useState(null);

  if (selected) {
    return (
      <main className="planner">
        <button className="text-button" onClick={() => setSelected(null)}>
          ← All events
        </button>
        <h1>Simulation {selected.id}</h1>
        <p className="intro">
          Demo data · Farm location {formatLocation(selected.location)}
        </p>

        <ul className="sources" aria-label="Simulated data sources">
          {["Elevation", "MODIS", "NASA POWER", "SoilGrids"].map((name) => (
            <li key={name}>{name} · Simulated success</li>
          ))}
        </ul>

        <div className="reports">
          {DEMO_ROTATIONS.map((rotation) => (
            <RotationCard key={rotation.rank} rotation={rotation} report />
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="planner">
      <h1>Events</h1>
      <p className="intro">
        Open a simulated run to see its scores and crop schedule.
      </p>
      <section className="panel">
        <div className="table-wrap">
          <table aria-label="Simulation runs">
            <thead>
              <tr>
                <th scope="col">Simulation</th>
                <th scope="col">Farm location</th>
                <th scope="col">Created</th>
                <th scope="col">Status</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <th scope="row">Simulation {run.id}</th>
                  <td>{formatLocation(run.location)}</td>
                  <td>
                    {run.createdAt
                      ? run.createdAt.toLocaleString()
                      : "Example run"}
                  </td>
                  <td>
                    <span className="status">Completed</span>
                  </td>
                  <td>
                    <button
                      className="view-button"
                      aria-label={`View simulation ${run.id}`}
                      onClick={() => setSelected(run)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function currentPage() {
  return window.location.hash === "#events" ? "events" : "home";
}

export default function App() {
  const [page, setPage] = useState(currentPage);
  const [runs, setRuns] = useState([
    { id: 1, location: EXAMPLE, createdAt: null },
  ]);
  const [point, setPoint] = useState(EXAMPLE);
  const [latitude, setLatitude] = useState(EXAMPLE.latitude.toFixed(6));
  const [longitude, setLongitude] = useState(EXAMPLE.longitude.toFixed(6));
  const [job, setJob] = useState(
    API_BASE
      ? null
      : {
          status: "COMPLETED",
          location: EXAMPLE,
          results: DEMO_ROTATIONS,
        }
  );
  const [sending, setSending] = useState(false);
  const [formError, setFormError] = useState("");
  const [pollError, setPollError] = useState("");
  const [sortBy, setSortBy] = useState("score");
  const [maxDays, setMaxDays] = useState("");

  const activeId = FINAL_STATUSES.includes(job?.status)
    ? null
    : job?.recommendation_id;

  useEffect(() => {
    function navigate() {
      setPage(currentPage());
      window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);

  const pickLocation = useCallback((lat, lng) => {
    setPoint({ latitude: lat, longitude: lng });
    setLatitude(lat.toFixed(6));
    setLongitude(lng.toFixed(6));
    setFormError("");
  }, []);

  useEffect(() => {
    if (!activeId) return;

    const controller = new AbortController();
    let timer;

    async function check() {
      try {
        const result = await request(
          `/rotations/${encodeURIComponent(activeId)}`,
          {
            signal: controller.signal,
          }
        );
        if (controller.signal.aborted) return;

        setJob(result);
        setPollError("");
        if (FINAL_STATUSES.includes(result.status)) return;
      } catch (error) {
        if (controller.signal.aborted) return;
        setPollError(`${error.message} Trying again in 10 seconds.`);
      }
      timer = setTimeout(check, 10000);
    }

    check();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [activeId]);

  async function submit(event) {
    event.preventDefault();
    const lat = Number(latitude);
    const lng = Number(longitude);

    if (
      !latitude.trim() ||
      !longitude.trim() ||
      Math.abs(lat) > 90 ||
      Math.abs(lng) > 180
    ) {
      setFormError("Enter a valid latitude and longitude.");
      return;
    }
    if (API_BASE && !insideNepal(lat, lng)) {
      setFormError("Choose coordinates inside Nepal.");
      return;
    }

    pickLocation(lat, lng);
    const location = { latitude: lat, longitude: lng };

    if (!API_BASE) {
      setJob({ status: "COMPLETED", location, results: DEMO_ROTATIONS });
      const createdAt = new Date();
      setRuns((items) => [
        { id: items.length + 1, location, createdAt },
        ...items,
      ]);
      return;
    }

    setSending(true);
    setJob(null);
    setPollError("");

    try {
      const accepted = await request("/rotations/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(location),
      });
      if (!accepted.recommendation_id) {
        throw new Error("The server returned no recommendation ID.");
      }
      setJob({
        ...accepted,
        location,
        status: accepted.job_status || "PENDING",
      });
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSending(false);
    }
  }

  const value = (rotation) =>
    (sortBy === "score" ? rotation.score : rotation.rotation_data?.[sortBy]) ??
    -1;

  const rotations = job?.results || [];
  const results = rotations
    .filter(
      (rotation) =>
        !maxDays ||
        (rotation.rotation_data?.total_days ?? Infinity) <= Number(maxDays)
    )
    .sort((a, b) => value(b) - value(a) || a.rank - b.rank);

  return (
    <div className="site">
      <header className="topbar">
        <a href="#home">AgriCycle</a>
        <span>Team Sunya</span>
      </header>

      <div className="site-body">
        <nav className="sidebar" aria-label="Main navigation">
          <a href="#home" aria-current={page === "home" ? "page" : undefined}>
            <span aria-hidden="true">⌂</span> Home
          </a>
          <a
            href="#events"
            aria-current={page === "events" ? "page" : undefined}
          >
            <span aria-hidden="true">▦</span> Events
          </a>
        </nav>

        {page === "events" ? (
          <Events runs={runs} />
        ) : (
          <main className="planner">
            <h1>Plan your next crop rotation</h1>
            <p className="intro">
              Choose a farm location and compare planting sequences.
            </p>

            <div className="layout">
              <section className="panel map-panel">
                <h2>Farm map</h2>
                <p>
                  Click the map or enter coordinates.{" "}
                  {API_BASE && "Live recommendations cover Nepal."}
                </p>
                <WorldMap point={point} onPick={pickLocation} />
              </section>

              <form className="panel form-panel" onSubmit={submit}>
                <h2>Farm location</h2>
                <label>
                  Latitude
                  <input
                    type="number"
                    step="any"
                    required
                    value={latitude}
                    onChange={(event) => setLatitude(event.target.value)}
                  />
                </label>
                <label>
                  Longitude
                  <input
                    type="number"
                    step="any"
                    required
                    value={longitude}
                    onChange={(event) => setLongitude(event.target.value)}
                  />
                </label>

                <button
                  className="action"
                  disabled={sending || Boolean(activeId)}
                >
                  {sending
                    ? "Submitting…"
                    : activeId
                    ? "Finding rotations…"
                    : API_BASE
                    ? "Get recommendations"
                    : "Preview crop rotations"}
                </button>

                <button
                  type="button"
                  className="text-button"
                  onClick={() =>
                    pickLocation(EXAMPLE.latitude, EXAMPLE.longitude)
                  }
                >
                  Use example location
                </button>
                {formError && (
                  <p role="alert" className="error">
                    {formError}
                  </p>
                )}
              </form>
            </div>

            <section className="results">
              <div className="results-header">
                <div>
                  <h2>
                    {API_BASE
                      ? "Recommended rotations"
                      : "Sample crop rotations"}
                  </h2>
                  {!API_BASE && (
                    <p>Demo values are the same for every location.</p>
                  )}
                </div>
                {rotations.length > 0 && (
                  <div className="filters">
                    <label>
                      Maximum days
                      <input
                        type="number"
                        min="1"
                        placeholder="Any"
                        value={maxDays}
                        onChange={(event) => setMaxDays(event.target.value)}
                      />
                    </label>
                    <label>
                      Sort by
                      <select
                        value={sortBy}
                        onChange={(event) => setSortBy(event.target.value)}
                      >
                        <option value="score">Overall score</option>
                        {METRICS.map(([key, label]) => (
                          <option key={key} value={key}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}
              </div>

              <div aria-live="polite">
                {activeId && <p>Preparing your recommendations…</p>}
                {job?.location && (
                  <p>
                    Farm location · {job.location.latitude},{" "}
                    {job.location.longitude}
                  </p>
                )}
                {pollError && <p className="error">{pollError}</p>}
                {job?.error_message && (
                  <p className="error">{job.error_message}</p>
                )}
                {job?.status === "FAILED" && !job.error_message && (
                  <p className="error">
                    The recommendation job failed. Try again.
                  </p>
                )}
                {job?.status === "PARTIAL_FAILED" && (
                  <p className="error">
                    Some farm data could not be retrieved.
                  </p>
                )}
                {job?.status === "COMPLETED" && !rotations.length && (
                  <p>No rotations were returned.</p>
                )}
                {rotations.length > 0 && !results.length && (
                  <p>No rotations fit the day limit.</p>
                )}
              </div>

              {job?.data_sources && (
                <ul className="sources" aria-label="Data source statuses">
                  {Object.entries(job.data_sources).map(([name, source]) => (
                    <li key={name}>
                      {name.replaceAll("_", " ")} · {source.status}
                    </li>
                  ))}
                </ul>
              )}

              <div className="rotation-grid">
                {results.map((rotation) => (
                  <RotationCard key={rotation.rank} rotation={rotation} />
                ))}
              </div>
            </section>
          </main>
        )}
      </div>
    </div>
  );
}
