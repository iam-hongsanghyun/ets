// Elastic baseline feature (Option A: price-elastic baseline). Owns the
// scenario-level reference_carbon_price field. Extracted verbatim from
// frontend/src/components/Editor.jsx, where it renders inline inside the
// Hotelling approach-params block (its pre-existing, if slightly unusual,
// visibility gate — preserved rather than "fixed", per the WO-F1 pixel/DOM
// equivalence bar). The hotelling feature imports ReferenceCarbonPriceField
// directly to embed it at that exact position; see features/hotelling.

export function ReferenceCarbonPriceField({ ctx }) {
  const { workingScenario, updateScenario } = ctx;
  return (
    <label>
      <span className="ekey">Reference carbon price (Option A) <span className="field-flag optional">optional</span></span>
      <input
        type="number"
        className="text"
        step="1"
        min="0"
        value={workingScenario.reference_carbon_price ?? 0.0}
        onChange={(e) => updateScenario({ reference_carbon_price: Math.max(0, parseFloat(e.target.value) || 0) })}
      />
      <span className="approach-params-hint">Price-elastic baseline anchor P_ref. Activity contracts when the price exceeds it. Set with each participant's output_price_elasticity. 0 = inelastic baseline (default).</span>
    </label>
  );
}

export default {
  id: "elastic_baseline",
  scenarioDefaults: {
    reference_carbon_price: 0.0,
  },
  approachOptions: [ReferenceCarbonPriceField],
};
