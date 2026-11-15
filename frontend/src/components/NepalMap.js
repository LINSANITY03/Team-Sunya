import React from "react";
import { MapContainer, TileLayer, CircleMarker, useMapEvents } from "react-leaflet";

const NEPAL_CENTER = [28.3949, 84.124];
const NEPAL_BOUNDS = [[26.2, 79.8], [30.6, 88.4]];

function ClickHandler({ onSelect }) {
  useMapEvents({
    click(e) {
      onSelect({ lat: +e.latlng.lat.toFixed(6), lng: +e.latlng.lng.toFixed(6) });
    },
  });
  return null;
}

export default function NepalMap({ position, onSelect }) {
  return (
    <MapContainer center={NEPAL_CENTER} zoom={7} minZoom={6}
      maxBounds={NEPAL_BOUNDS} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onSelect={onSelect} />
      {position && (
        <CircleMarker center={[position.lat, position.lng]} radius={9}
          pathOptions={{ color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.9 }} />
      )}
    </MapContainer>
  );
}