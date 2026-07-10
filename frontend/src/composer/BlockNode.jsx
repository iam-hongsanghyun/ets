import { Handle, Position } from "@xyflow/react";

// Generic node renderer driven entirely by the block's catalogue spec
// (data.block). No per-block-kind branching — every block category renders
// through this same component, styled only by a CSS category class.
function BlockNode({ data, selected }) {
  const block = data.block;
  const inputs = block?.ports?.inputs || [];
  const outputs = block?.ports?.outputs || [];
  const rowCount = Math.max(inputs.length, outputs.length, 1);

  return (
    <div className={`composer-node cat-${data.category} ${selected ? "selected" : ""}`}>
      <div className="composer-node-head">
        <span className="composer-node-category">{data.category}</span>
        <span className="composer-node-label">{data.label}</span>
      </div>
      <div className="composer-node-ports" style={{ "--rows": rowCount }}>
        {Array.from({ length: rowCount }).map((_, rowIndex) => (
          <div className="composer-node-port-row" key={rowIndex}>
            <div className="composer-node-port-cell composer-node-port-cell-in">
              {inputs[rowIndex] && (
                <>
                  <Handle
                    type="target"
                    position={Position.Left}
                    id={inputs[rowIndex].name}
                    className="composer-handle composer-handle-in"
                  />
                  <span className="composer-port-label">{inputs[rowIndex].name}</span>
                </>
              )}
            </div>
            <div className="composer-node-port-cell composer-node-port-cell-out">
              {outputs[rowIndex] && (
                <>
                  <span className="composer-port-label">{outputs[rowIndex].name}</span>
                  <Handle
                    type="source"
                    position={Position.Right}
                    id={outputs[rowIndex].name}
                    className="composer-handle composer-handle-out"
                  />
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export { BlockNode };
