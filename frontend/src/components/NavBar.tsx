import { NavLink } from "react-router-dom";
import { DatabaseSelector } from "./DatabaseSelector";

const links = [
  { to: "/query", label: "Query" },
  { to: "/schema", label: "Schema" },
  { to: "/history", label: "History" },
  { to: "/evaluation", label: "Evaluation" },
];

export function NavBar() {
  return (
    <header className="top-nav">
      <span className="brand">Chat with SQL</span>
      <nav>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <DatabaseSelector />
    </header>
  );
}
