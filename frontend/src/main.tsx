import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import { App } from "./App.tsx";
import { DatabaseProvider } from "./context/DatabaseContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <DatabaseProvider>
        <App />
      </DatabaseProvider>
    </BrowserRouter>
  </StrictMode>
);
