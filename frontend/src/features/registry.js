// Frontend feature-module registry — the reviewed composition point that
// mirrors the backend wiring-literal doctrine (see docs/feature-modules-plan.md):
// a static literal, no dynamic registration, no import-order effects.
//
// Each feature's index.jsx default-exports a "fragment" object with the
// shape (all slots optional):
//   {
//     id: string,
//     scenarioDefaults: object,          // merged into makeBlankScenario()
//     participantDefaults: object,       // merged into makeBlankParticipant()
//     editorSections: [Component],       // scenario/market-level editor UI
//     participantEditorSections: [Component], // participant-level editor UI
//     approachOptions: [Component],      // model_approach-gated solver params
//     validators: [fn],                  // scenario -> issue[] (see AppShared.validateScenario)
//     guideSections: [...],              // reserved for the guide view (not wired yet)
//   }
//
// This module (WO-F1) wires the editor/config side only: makeBlankScenario,
// makeBlankParticipant, validateScenario, and the Editor's editorSections /
// participantEditorSections / approachOptions slots. Result-side fragments
// (WO-F2) and the pe shell's enabledFeatures filtering UI (WO-F3) land later.

import msr from "./msr/index.jsx";
import ccr from "./ccr/index.jsx";
import cbam from "./cbam/index.jsx";
import sectors from "./sectors/index.jsx";
import oba from "./oba/index.jsx";
import price_controls from "./price_controls/index.jsx";
import banking from "./banking/index.jsx";
import hotelling from "./hotelling/index.jsx";
import nash_cournot from "./nash_cournot/index.jsx";
import transmission from "./transmission/index.jsx";
import elastic_baseline from "./elastic_baseline/index.jsx";
import calibration from "./calibration/index.jsx";

export const FEATURES = Object.freeze({
  msr,
  ccr,
  cbam,
  sectors,
  oba,
  price_controls,
  banking,
  hotelling,
  nash_cournot,
  transmission,
  elastic_baseline,
  calibration,
});

// enabledFeatures === null means "all features" (today's default shell).
// A provided array restricts composition to those ids, in FEATURES'
// (registry-literal) order — the array's own order is not significant.
export function activeFeatureIds(enabledFeatures) {
  if (enabledFeatures == null) return Object.keys(FEATURES);
  const enabled = new Set(enabledFeatures);
  return Object.keys(FEATURES).filter((id) => enabled.has(id));
}

// Flatten a named slot across active features, in registry order. Pass
// featureIds to scope the collection to a subset of features (used where a
// host location renders only one feature's contribution to a slot, e.g. the
// "Sectors" panel is sectors-only even though other features also
// contribute editorSections elsewhere in the editor).
export function collectSlot(enabledFeatures, slotName, featureIds = null) {
  const active = activeFeatureIds(enabledFeatures);
  const scoped = featureIds ? active.filter((id) => featureIds.includes(id)) : active;
  return scoped
    .map((id) => FEATURES[id])
    .filter(Boolean)
    .flatMap((feature) => feature[slotName] || []);
}
