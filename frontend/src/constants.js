// type: int | float | text | bool | date | slider | select

// Shown first
export const PRIORITY_SLIDERS = [
  { key: "profit", label: "Profit", type: "slider", default: 0.5 },
  { key: "food_security", label: "Food security", type: "slider", default: 0.25 },
  { key: "soil_health", label: "Soil health", type: "slider", default: 0.25 },
  { key: "water_saving", label: "Water saving", type: "slider", default: 0.25 },
  { key: "low_risk", label: "Low risk", type: "slider", default: 0.3 },
];

export const PRIORITY_BASICS = [
  { key: "irrigation", label: "Irrigated", type: "bool", default: false },
  { key: "start_date", label: "Start date", type: "date", default: "2026-11-01" },
  { key: "field_id", label: "Field ID", type: "text", default: "field_001" },
];

// Collapsed by default
export const ADVANCED_SECTIONS = [
  {
    title: "Rotation",
    fields: [
      { key: "rotation_length", label: "Rotation length (crop cycles)", type: "int", default: 3, min: 1 },
      { key: "max_candidates", label: "Max candidates", type: "int", default: 50000, min: 1 },
      { key: "default_family_gap", label: "Default family gap (cycles)", type: "int", default: 2, min: 0,
        help: "Same family must be at least this many cycles apart" },
      { key: "cyclic", label: "Cyclic rotation", type: "bool", default: true,
        help: "Last → first also counts for family gap" },
      { key: "require_legume", label: "Require at least one legume / green manure", type: "bool", default: false },
    ],
  },
  {
    title: "Soil",
    fields: [
      { key: "bd_reject", label: "Bulk density reject (kg/dm³)", type: "float", default: 1.75, min: 0, step: 0.05,
        help: "At or above this, roots are blocked" },
      { key: "clay_max_root_crops", label: "Max clay for root crops (%)", type: "float", default: 55, min: 0, max: 100,
        help: "Reject tuber/root crops above this" },
      { key: "min_soil_depth_ratio", label: "Min soil depth ratio", type: "float", default: 0.5, min: 0, max: 1, step: 0.05,
        help: "Soil depth ≥ this fraction of rooting depth" },
      { key: "n_ok_g_per_kg", label: "Soil N OK (g/kg)", type: "float", default: 2, min: 0, step: 0.1 },
    ],
  },
  {
    title: "Timing",
    fields: [
      { key: "turnaround_days", label: "Turnaround days", type: "int", default: 10, min: 0,
        help: "Land prep between harvest and next sowing" },
      { key: "max_fallow_days", label: "Max fallow days", type: "int", default: 120, min: 0,
        help: "Longest acceptable idle gap between crops" },
      { key: "max_horizon_days", label: "Max horizon days", type: "int", default: 800, min: 1,
        help: "Whole rotation must finish within this" },
      { key: "max_single_crop_days", label: "Max single crop days", type: "int", default: 300, min: 1,
        help: "Longer = perennial / not rotatable" },
      { key: "harvest_mismatch_tol_days", label: "Harvest mismatch tolerance (days)", type: "int", default: 20, min: 0,
        help: "Data-quality flag only" },
    ],
  },
  {
    title: "Water",
    fields: [
      { key: "rain_eff", label: "Effective rain fraction", type: "float", default: 0.8, min: 0, max: 1, step: 0.05 },
      { key: "min_wet_low", label: "Min wetness at low demand (2 mm/d)", type: "float", default: 0.25, min: 0, max: 1, step: 0.05 },
      { key: "min_wet_high", label: "Min wetness at high demand (6 mm/d)", type: "float", default: 0.55, min: 0, max: 1, step: 0.05 },
      { key: "water_reject_ratio", label: "Water reject ratio", type: "float", default: 0.2, min: 0, max: 1, step: 0.05 },
    ],
  },
];

export const FAILED_STATUSES = ["FAILED", "ERROR"];