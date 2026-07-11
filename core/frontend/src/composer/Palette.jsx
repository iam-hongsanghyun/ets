import { useMemo } from "react";

// Renders entirely from the block catalogue fetched from GET /api/blocks (or
// the dev fixture) — no category list or block metadata is hardcoded here.
function Palette({ blocks }) {
  const groups = useMemo(() => {
    const byCategory = new Map();
    blocks.forEach((block) => {
      if (!byCategory.has(block.category)) byCategory.set(block.category, []);
      byCategory.get(block.category).push(block);
    });
    return Array.from(byCategory.entries()).map(([category, items]) => ({
      category,
      items: items.slice().sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [blocks]);

  const handleDragStart = (event, blockId) => {
    event.dataTransfer.setData("application/x-composer-block", blockId);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="composer-palette">
      {groups.map((group) => (
        <div className="composer-palette-group" key={group.category}>
          <div className={`composer-palette-group-title cat-${group.category}`}>{group.category}</div>
          <div className="composer-palette-items">
            {group.items.map((block) => (
              <div
                key={block.id}
                className={`composer-palette-item cat-${group.category}`}
                draggable
                onDragStart={(event) => handleDragStart(event, block.id)}
                title={block.doc || ""}
              >
                {block.label}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export { Palette };
