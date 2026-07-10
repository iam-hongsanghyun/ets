// Calibration feature — Nelder-Mead solver tuning for scenario calibration.
// Extracted verbatim from frontend/src/components/Editor.jsx (Calibration
// solver group, market step). No defaults exist in makeBlankScenario today
// (the fields fall back to their in-editor defaults via `??`), so
// scenarioDefaults is intentionally omitted here.

import { CollapsibleGroup, numInput } from "../../components/EditorPrimitives.jsx";

function CalibrationEditorSection({ ctx }) {
  const { workingScenario, updateScenario } = ctx;
  return (
    <CollapsibleGroup title="Calibration solver" defaultOpen={false}>
      <div className="solver-settings-grid">
        <label>
          <span className="ekey">Calibration xatol <span className="field-flag optional">optional</span></span>
          <span className="solver-settings-desc">Nelder-Mead slope change tolerance. Smaller = tighter fit but slower. Default: 0.1</span>
          {numInput(workingScenario.solver_calibration_xatol ?? 0.1, (v) => updateScenario({ solver_calibration_xatol: Math.max(1e-6, v) }), 0.01, 1e-6)}
        </label>
        <label>
          <span className="ekey">Calibration fatol <span className="field-flag optional">optional</span></span>
          <span className="solver-settings-desc">Nelder-Mead MSE change tolerance. Smaller = tighter fit but slower. Default: 0.01</span>
          {numInput(workingScenario.solver_calibration_fatol ?? 0.01, (v) => updateScenario({ solver_calibration_fatol: Math.max(1e-8, v) }), 0.001, 1e-8)}
        </label>
      </div>
    </CollapsibleGroup>
  );
}

export default {
  id: "calibration",
  editorSections: [CalibrationEditorSection],
};
