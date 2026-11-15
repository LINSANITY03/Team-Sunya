import React, { useState } from "react";
import { FORM_FIELDS } from "../constants";

const initial = () =>
  Object.fromEntries(FORM_FIELDS.map((f) => [f.key, f.default]));

export default function ParamsSheet({ position, onSubmit, submitting, onClose }) {
  const [values, setValues] = useState(initial);
  const open = !!position;

  const change = (f, v) =>
    setValues((s) => ({ ...s, [f.key]: f.type === "number" ? Number(v) : v }));

  return (
    <div className={"sheet" + (open ? " open" : "")}>
      <div className="sheet-head">
        <strong>
          {position ? `Selected: ${position.lat}, ${position.lng}` : ""}
        </strong>
        <button className="btn-ghost" onClick={onClose}>✕</button>
      </div>

      <div className="sheet-scroll">
        {FORM_FIELDS.map((f) => (
          <label key={f.key} className="field">
            <span>{f.label}</span>
            {f.type === "select" ? (
              <select value={values[f.key]} onChange={(e) => change(f, e.target.value)}>
                {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <input type={f.type} value={values[f.key]} min={f.min} max={f.max}
                step={f.step} onChange={(e) => change(f, e.target.value)} />
            )}
          </label>
        ))}
      </div>

      <div className="sheet-foot">
        <button className="btn" disabled={submitting || !position}
          onClick={() => onSubmit({
            latitude: position.lat,
            longitude: position.lng,
            ...values,
          })}>
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>
    </div>
  );
}