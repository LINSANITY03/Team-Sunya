import React, { useState } from "react";
import { Link } from "react-router-dom";
import NepalMap from "../components/NepalMap";
import ParamsSheet from "../components/ParamsSheet";
import { createRecommendation } from "../api";

export default function Dashboard() {
  const [position, setPosition] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const submit = async (payload) => {
    setSubmitting(true); setError(null); setResult(null);
    try {
      setResult(await createRecommendation(payload));
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dash">
      <div className="map-wrap">
        <NepalMap position={position} onSelect={(p) => { setPosition(p); setResult(null); }} />
        {!position && <div className="hint">Click anywhere on the map of Nepal to choose a location</div>}
      </div>

      {result && (
        <div className="toast ok">
          {result.message} ID: <code>{result.recommendation_id}</code>{" "}
          <Link to="/events">View events →</Link>
        </div>
      )}
      {error && <div className="toast err">{error}</div>}

      <ParamsSheet position={position} submitting={submitting}
        onSubmit={submit} onClose={() => setPosition(null)} />
    </div>
  );
}