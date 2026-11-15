import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRotations, deleteRotation } from "../api";
import { FAILED_STATUSES } from "../constants";

const LIMIT = 10;

export default function Events() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setData(await listRotations(page, LIMIT));
      setError(null);
    } catch (e) { setError(e.message); }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  // poll while anything is still being processed
  const hasPending = data?.recommendations?.some(
    (r) => r.status !== "COMPLETED" && !FAILED_STATUSES.includes(r.status)
  );
  useEffect(() => {
    if (!hasPending) return;
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [hasPending, load]);

  const remove = async (id) => {
    if (!window.confirm("Delete this recommendation?")) return;
    try { await deleteRotation(id); load(); } catch (e) { setError(e.message); }
  };

  if (!data && !error) return <p className="pad">Loading…</p>;

  return (
    <div className="pad">
      <h2>Events</h2>
      {error && <div className="toast err static">{error}</div>}

      <ul className="list">
        {data?.recommendations.map((r) => {
          const done = r.status === "COMPLETED";
          const failed = FAILED_STATUSES.includes(r.status);
          return (
            <li key={r.recommendation_id} className="row">
              <div>
                <div className="mono">{r.recommendation_id}</div>
                <div className="muted">
                  {r.location.latitude}, {r.location.longitude} ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </div>
                {failed && r.error_message && <div className="err-text">{r.error_message}</div>}
              </div>
              <div className="actions">
                {done ? (
                  <>
                    <button className="btn" onClick={() => navigate(`/events/${r.recommendation_id}`)}>View</button>
                    <button className="btn danger" onClick={() => remove(r.recommendation_id)}>Delete</button>
                  </>
                ) : failed ? (
                  <>
                    <span className="badge fail">{r.status}</span>
                    <button className="btn danger" onClick={() => remove(r.recommendation_id)}>Delete</button>
                  </>
                ) : (
                  <span className="badge proc">Processing…</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {data && data.total_pages > 1 && (
        <div className="pager">
          <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
          <span>Page {data.page} / {data.total_pages}</span>
          <button className="btn" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}