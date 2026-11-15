import React, { useState, useRef, useEffect } from "react";
import { PRIORITY_SLIDERS, PRIORITY_BASICS, ADVANCED_SECTIONS } from "../constants";

const allFields = [
  ...PRIORITY_SLIDERS,
  ...PRIORITY_BASICS,
  ...ADVANCED_SECTIONS.flatMap((s) => s.fields),
];
const initialValues = () =>
  Object.fromEntries(allFields.map((f) => [f.key, f.default]));

function buildPayload(values) {
  const out = {};
  for (const f of allFields) {
    const v = values[f.key];
    if (f.type === "int" || f.type === "float") {
      const n = f.type === "int" ? parseInt(v, 10) : parseFloat(v);
      if (Number.isNaN(n)) throw new Error(`${f.label}: enter a number`);
      if (f.min !== undefined && n < f.min) throw new Error(`${f.label}: minimum is ${f.min}`);
      if (f.max !== undefined && n > f.max) throw new Error(`${f.label}: maximum is ${f.max}`);
      out[f.key] = n;
    } else if (f.type === "slider") {
      out[f.key] = Number(v);
    } else if (f.type === "text") {
      if (!String(v).trim()) throw new Error(`${f.label} is required`);
      out[f.key] = String(v).trim();
    } else {
      out[f.key] = v; // bool, date (yyyy-mm-dd)
    }
  }
  return out;
}

export default function ParamsSheet({ position, open, onSubmit, submitting, onClose }) {
  const [values, setValues] = useState(initialValues);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [formError, setFormError] = useState(null);

  const setVal = (key, v) => setValues((s) => ({ ...s, [key]: v }));

  const submit = () => {
    try {
      const params = buildPayload(values);
      setFormError(null);
      onSubmit({ latitude: position.lat, longitude: position.lng, ...params });
    } catch (e) {
      setFormError(e.message);
    }
  };

  const advRef = useRef(null);

  useEffect(() => {
    if (showAdvanced && advRef.current) {
      // wait for the sections to render, then scroll to them
      requestAnimationFrame(() => {
        advRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [showAdvanced]);

  const renderSlider = (f) => (
    <label key={f.key} className="slider">
      <div className="slider-top">
        <span>{f.label}</span>
        <strong>{Number(values[f.key]).toFixed(2)}</strong>
      </div>
      <input type="range" min="0" max="1" step="0.05" value={values[f.key]}
        onChange={(e) => setVal(f.key, e.target.value)} />
    </label>
  );

  const renderField = (f) => {
    if (f.type === "bool") {
      return (
        <label key={f.key} className="check">
          <input type="checkbox" checked={!!values[f.key]}
            onChange={(e) => setVal(f.key, e.target.checked)} />
          <span>{f.label}{f.help && <em className="help"> — {f.help}</em>}</span>
        </label>
      );
    }
    return (
      <label key={f.key} className="field">
        <span>{f.label}</span>
        <input
          type={f.type === "int" || f.type === "float" ? "number" : f.type}
          value={values[f.key]} min={f.min} max={f.max}
          step={f.step ?? (f.type === "int" ? 1 : "any")}
          onChange={(e) => setVal(f.key, e.target.value)} />
        {f.help && <small className="help">{f.help}</small>}
      </label>
    );
  };

  return (
    <div className={"sheet" + (open ? " open" : "")}>
      <div className="sheet-head">
      <div>
        <strong>Crop rotation settings</strong>
        <div className="muted">
          {position ? `Location: ${position.lat}, ${position.lng}` : ""}
        </div>
      </div>
      <button className="btn-ghost" onClick={onClose} aria-label="Back to map">✕</button>
    </div>

      <div className="sheet-scroll">
        {/* PRIORITIES (always visible) */}
        <fieldset className="section">
          <legend>Priorities</legend>
          <p className="help" style={{ margin: "0 0 10px" }}>
            0 = not important, 1 = very important
          </p>
          <div className="grid2">{PRIORITY_SLIDERS.map(renderSlider)}</div>
          <div className="grid2" style={{ marginTop: 14 }}>
            {PRIORITY_BASICS.map(renderField)}
          </div>
        </fieldset>

        {/* ADVANCED (collapsed by default) */}
        <button type="button" className="adv-toggle"
          onClick={() => setShowAdvanced((s) => !s)}>
          {showAdvanced ? "▾" : "▸"} Advanced options
        </button>

        {showAdvanced && (
          <div ref={advRef} className="adv-wrap">
            {ADVANCED_SECTIONS.map((s) => (
              <fieldset key={s.title} className="section">
                <legend>{s.title}</legend>
                <div className="grid2">{s.fields.map(renderField)}</div>
              </fieldset>
            ))}
          </div>
        )}
      </div>

      <div className="sheet-foot">
        {formError && <div className="err-text" style={{ marginBottom: 8 }}>{formError}</div>}
        <button className="btn" disabled={submitting || !position} onClick={submit}>
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>
    </div>
  );
}