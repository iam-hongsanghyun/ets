import { useEffect, useState } from "react";
import App from "../app.jsx";

// PE — model-scoped shell. Reached only via `?mode=pe` (see main.jsx).
// LANDING: a plain list of models from GET /api/templates (this file does
// not know or care how many there are — the backend example suite grows
// independently of this UI). SELECTED: GET /api/model-manifest?id=<id> to
// resolve the model's feature-module subset, then mount the SAME App
// component the default shell uses (App({ enabledFeatures, initialTemplateId }))
// so every registry-driven host (Editor's editorSections /
// participantEditorSections / approachOptions, AnalysisView's
// analysisBullets / summaryPanels, ParticipantPanel's resultStats,
// AppShared's makeBlankScenario / makeBlankParticipant / validateScenario)
// filters automatically — WO-F1/F2 already thread enabledFeatures through
// the registry collectors; this shell only supplies the value.
//
// No new CSS: reuses .hdr/.hdr-top/.hdr-brand/.hdr-tools (main Header),
// .panel/.panel-head/.eyebrow (AppShared/AppViews panels),
// .builder-list/.builder-list-item/.builder-item-meta (Editor's
// participant/technology picker lists), .pill-btn (Header's scenario
// pills, reused here as plain module-name chips), .ghost-btn, and the
// .server-warnings-* banner (App's own run-warnings banner).

function sourceLabel(template) {
  if (template.source === "user") return "User model";
  if (template.source === "example") return "Example";
  return "Blank";
}

function ModelGroup({ eyebrow, title, description, templates, onSelect }) {
  if (!templates.length) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">{eyebrow}</div>
          <h2>{title}</h2>
          <p className="muted">{description}</p>
        </div>
      </div>
      <div className="builder-list">
        {templates.map((template) => (
          <button
            key={template.id}
            type="button"
            className="builder-list-item"
            onClick={() => onSelect(template.id)}
          >
            <span>{template.name}</span>
            <span className="builder-item-meta">{sourceLabel(template)}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function ModelLanding({ templates, status, error, onDismissError, onSelect }) {
  const examples = templates.filter((template) => template.source === "example");
  const userModels = templates.filter((template) => template.source === "user");
  const other = templates.filter((template) => template.source !== "example" && template.source !== "user");
  return (
    <div className="app">
      <header className="hdr">
        <div className="hdr-top">
          <div className="hdr-brand">
            <div>
              <div className="brand-title">Clearing — PE</div>
              <div className="brand-sub">{status}</div>
            </div>
          </div>
        </div>
      </header>
      {error && (
        <div className="server-warnings-banner">
          <span className="server-warnings-icon">⚠</span>
          <div className="server-warnings-list">
            <div className="server-warning-item">{error}</div>
          </div>
          <button className="server-warnings-close" onClick={onDismissError} title="Dismiss">✕</button>
        </div>
      )}
      <div className="wb">
        <section className="wb-hero">
          <div className="scenario-meta">
            <div className="eyebrow">Start</div>
            <h1>Choose a model</h1>
            <p className="lede">Every model opens with only the modules it actually uses — no unrelated MSR, CCR, CBAM, sector, or OBA sections.</p>
          </div>
        </section>
        <ModelGroup
          eyebrow="Start"
          title="Blank configuration"
          description="An empty scenario, built up from scratch."
          templates={other}
          onSelect={onSelect}
        />
        <ModelGroup
          eyebrow="Examples"
          title="Example models"
          description="Pre-built scenarios, each exercising a specific policy mechanism."
          templates={examples}
          onSelect={onSelect}
        />
        <ModelGroup
          eyebrow="Your models"
          title="Saved models"
          description="Models saved to the local registry."
          templates={userModels}
          onSelect={onSelect}
        />
        {!templates.length && status === "Loaded" && (
          <section className="panel">
            <div className="builder-empty large">No models found.</div>
          </section>
        )}
      </div>
    </div>
  );
}

function ModelToolbar({ name, features, onBack }) {
  return (
    <header className="hdr">
      <div className="hdr-top">
        <div className="hdr-brand">
          <div>
            <div className="brand-title">{name}</div>
            <div className="brand-sub">pe model</div>
          </div>
        </div>
        <div className="hdr-tools">
          <button className="ghost-btn" type="button" onClick={onBack}>Back to models</button>
        </div>
      </div>
      <div className="hdr-scenarios">
        {(features || []).map((feature) => (
          <span key={feature} className="pill-btn on">{feature}</span>
        ))}
      </div>
    </header>
  );
}

export function PeApp() {
  const [templates, setTemplates] = useState([]);
  const [status, setStatus] = useState("Loading…");
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null); // { id, name, features }

  useEffect(() => {
    let cancelled = false;
    fetch("/api/templates")
      .then((response) => response.json())
      .then((payload) => {
        if (cancelled) return;
        setTemplates(payload.templates || []);
        setStatus("Loaded");
      })
      .catch(() => {
        if (!cancelled) setStatus("Load failed");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function selectModel(templateId) {
    setError(null);
    setStatus("Loading model…");
    try {
      const response = await fetch(`/api/model-manifest?id=${encodeURIComponent(templateId)}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "This model's manifest could not be loaded.");
      }
      const template = templates.find((item) => item.id === templateId);
      setSelected({
        id: templateId,
        name: template?.name || templateId,
        features: payload.features || null,
      });
      setStatus("Loaded");
    } catch (err) {
      setError(err.message || "This model could not be loaded.");
      setStatus("Loaded");
    }
  }

  function backToModels() {
    setSelected(null);
    setError(null);
  }

  if (!selected) {
    return (
      <ModelLanding
        templates={templates}
        status={status}
        error={error}
        onDismissError={() => setError(null)}
        onSelect={selectModel}
      />
    );
  }

  return (
    <div className="app">
      <ModelToolbar name={selected.name} features={selected.features} onBack={backToModels} />
      <App key={selected.id} enabledFeatures={selected.features} initialTemplateId={selected.id} />
    </div>
  );
}
