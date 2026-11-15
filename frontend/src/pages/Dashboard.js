import React, { useState } from "react";
import { Link } from "react-router-dom";
import NepalMap from "../components/NepalMap";
import ParamsSheet from "../components/ParamsSheet";
import { createRecommendation } from "../api";

export default function Dashboard() {
  const [position, setPosition] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSelect = (p) => {
    setPosition(p);
    setFormOpen(true);
    setResult(null);
    setError(null);
  };

  const submit = async (payload) => {
    console.log("payload", payload);
    setSubmitting(true); setError(null); setResult(null);
    try {
      setResult(await createRecommendation(payload));
      setFormOpen(false);          // back to the map after success
    } catch (e) {
      setError(e.message);         // stay on the form so the user can fix it
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dash">
      <div className="map-wrap">
        <NepalMap position={position} onSelect={handleSelect} />
        {!position && (
          <div className="hint">Click anywhere on the map of Nepal to choose a location</div>
        )}
      </div>

      {result && (
        <div className="toast ok">
          {result.message} ID: <code>{result.recommendation_id}</code>{" "}
          <Link to="/events">View events →</Link>
        </div>
      )}
      {error && <div className="toast err">{error}</div>}

      <ParamsSheet
        position={position}
        open={formOpen}
        submitting={submitting}
        onSubmit={submit}
        onClose={() => setFormOpen(false)}
      />
    </div>
  );
}