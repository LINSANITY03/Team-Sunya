export const FORM_FIELDS = [
    { key: "start_date", label: "Planting start date", type: "date", default: "2026-03-01" },
    { key: "planning_months", label: "Planning horizon (months)", type: "number", default: 12, min: 3, max: 36 },
    { key: "irrigation", label: "Water source", type: "select", default: "rainfed",
      options: ["rainfed", "irrigated", "partial"] },
    { key: "goal", label: "Main goal", type: "select", default: "balanced",
      options: ["balanced", "profit", "food", "soil_health"] },
    { key: "max_crops", label: "Crops per rotation", type: "number", default: 3, min: 2, max: 5 },
    { key: "land_area_ha", label: "Land area (hectares)", type: "number", default: 1, min: 0.1, step: 0.1 },
  ];
  
  export const PROCESSED_STATUSES = ["COMPLETED"];
  export const FAILED_STATUSES = ["FAILED", "ERROR"];