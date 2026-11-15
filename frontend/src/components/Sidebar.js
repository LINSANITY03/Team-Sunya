import React from "react";
import { NavLink } from "react-router-dom";

const items = [
  { label: "home", to: "/" },
  { label: "events", to: "/events" },
];

export default function Sidebar() {
  return (
    <nav className="sidebar">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.to === "/"}
          className={({ isActive }) => "side-link" + (isActive ? " active" : "")}>
          {i.label}
        </NavLink>
      ))}
    </nav>
  );
}