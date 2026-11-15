const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = JSON.stringify(await res.json()); } catch (e) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

export const createRecommendation = (payload) =>
  request("/rotations/recommend", { method: "POST", body: JSON.stringify(payload) });

export const listRotations = (page = 1, limit = 10) =>
  request(`/rotations/?page=${page}&limit=${limit}`);

export const getRotation = (id) => request(`/rotations/${id}`);

export const deleteRotation = (id) =>
  request(`/rotations/${id}`, { method: "DELETE" });