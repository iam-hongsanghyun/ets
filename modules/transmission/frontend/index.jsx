// Transmission feature — placeholder module for WO-F1.
//
// No transmission-specific editor UI exists in Editor.jsx today (no
// model_approach option, no solver-tuning block), so there is nothing to
// extract for the editor/config side of this order. Registered now so the
// registry-literal composition order is stable ahead of WO-F2/F3.

// ── Guide: pe-shell module section (only rendered when this model uses
// forward transmission — see frontend/src/components/GuideView.jsx).

function TransmissionGuideSection() {
  return (
    <div className="guide-body">
      <p className="guide-lead">
        <strong>Forward transmission</strong> blends this year's cleared price with a
        forward-looking price signal using a λ weight (0 = fully current-year, 1 = fully
        forward), letting expected future scarcity propagate into today's equilibrium.
      </p>
      <div className="guide-tip">
        <strong>Note:</strong> forward transmission is configured on the loaded model's
        underlying config (<code>forward_transmission_lambda</code>) — there is no dedicated
        editor panel for it yet.
      </div>
    </div>
  );
}

export default {
  id: "transmission",
  guideSections: [{ id: "module-transmission", tag: "TRANS", title: "Forward transmission", content: TransmissionGuideSection }],
};
