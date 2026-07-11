import ReactDOM from "react-dom/client";
import App from "./app.jsx";
import { ComposerAdmin } from "./composer/ComposerAdmin.jsx";
import { PeApp } from "./pe/PeApp.jsx";

// Three-way mode switch on window.location.search:
//   ?mode=composer -> ComposerAdmin (admin GUI, reached via configure.command)
//   ?mode=pe       -> PeApp (model-scoped shell, reached via pe.command)
//   (anything else)-> App with enabledFeatures=null (the everything-shell)
// Neither admin shell is a tab of the main app; the main app never renders
// them, and they never render the main app's own Model/Validation/
// Analysis/Scenario/Guide tabs directly (PeApp mounts App itself, scoped).
const mode = new URLSearchParams(window.location.search).get("mode");

const view =
  mode === "composer" ? <ComposerAdmin />
  : mode === "pe" ? <PeApp />
  : <App enabledFeatures={null} />;

ReactDOM.createRoot(document.getElementById("root")).render(view);
