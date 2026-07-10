import ReactDOM from "react-dom/client";
import App from "./app.jsx";
import { ComposerAdmin } from "./composer/ComposerAdmin.jsx";

// The Composer is a separate admin GUI, not a tab of the main app: it is
// reached only via `?mode=composer` on the URL (see configure.command), and
// the main app never renders it.
const isComposerAdmin = window.location.search === "?mode=composer";

ReactDOM.createRoot(document.getElementById("root")).render(
  isComposerAdmin ? <ComposerAdmin /> : <App />
);
