import { Composer } from "./Composer.jsx";

// Standalone admin shell for the graph Composer. Reached only via
// `?mode=composer` (see main.jsx) — never mounted inside the main app, and
// carries none of the main app's Model/Validation/Analysis/Scenario/Guide
// tabs. Reuses the `.hdr`/`.hdr-top`/`.hdr-brand`/`.brand-title` classes the
// main Header already defines instead of inventing new header CSS.
function ComposerAdmin() {
  return (
    <div className="app">
      <header className="hdr">
        <div className="hdr-top">
          <div className="hdr-brand">
            <div className="brand-title">Model Composer — Admin</div>
          </div>
        </div>
      </header>
      <Composer />
    </div>
  );
}

export { ComposerAdmin };
