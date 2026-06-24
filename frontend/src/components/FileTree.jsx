import { useState } from "react";

function TreeNode({ name, node, depth, onFileClick }) {
  const [open, setOpen] = useState(depth < 1);
  const isFile = node.__type__ === "file";

  if (isFile) {
    return (
      <div
        className="flex items-center gap-2 py-1 px-2 rounded hover:bg-base-800 cursor-pointer text-sm"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => onFileClick?.(name, node)}
      >
        <span className="text-ink-faint font-mono text-xs">·</span>
        <span className="text-ink-dim truncate">{name}</span>
        <span className="text-ink-faint text-xs ml-auto font-mono">{node.language}</span>
      </div>
    );
  }

  const children = node.__children__ || {};
  const entries = Object.entries(children).sort(([aName, aNode], [bName, bNode]) => {
    const aIsDir = aNode.__type__ !== "file";
    const bIsDir = bNode.__type__ !== "file";
    if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
    return aName.localeCompare(bName);
  });

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1 px-2 rounded hover:bg-base-800 cursor-pointer text-sm"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => setOpen(!open)}
      >
        <span className="text-accent font-mono text-xs w-3">{open ? "▾" : "▸"}</span>
        <span className="text-ink font-medium truncate">{name}</span>
      </div>
      {open && (
        <div>
          {entries.map(([childName, childNode]) => (
            <TreeNode
              key={childName}
              name={childName}
              node={childNode}
              depth={depth + 1}
              onFileClick={onFileClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({ tree, onFileClick }) {
  if (!tree || Object.keys(tree).length === 0) {
    return <p className="text-ink-faint text-sm px-2">No files to display.</p>;
  }

  const entries = Object.entries(tree).sort(([aName, aNode], [bName, bNode]) => {
    const aIsDir = aNode.__type__ !== "file";
    const bIsDir = bNode.__type__ !== "file";
    if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
    return aName.localeCompare(bName);
  });

  return (
    <div className="font-mono">
      {entries.map(([name, node]) => (
        <TreeNode key={name} name={name} node={node} depth={0} onFileClick={onFileClick} />
      ))}
    </div>
  );
}
