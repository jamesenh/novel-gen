import { useMemo, useState } from "react";
import clsx from "clsx";
import { Character, CharactersData } from "../types";

type Props = {
  data: CharactersData;
  onChange: (newData: CharactersData) => void;
};

type NodeType = "protagonist" | "antagonist" | "support";

type Node = {
  id: string;
  x: number;
  y: number;
  data: Character;
  type: NodeType;
};

// 布局常量
const CANVAS_WIDTH = 1000;
const CANVAS_HEIGHT = 600;
const NODE_WIDTH = 160;
const NODE_HEIGHT = 90;
const LABEL_WRAP = 12;

const wrapLabel = (label?: string, max = LABEL_WRAP) => {
  if (!label) return [];
  const chars = Array.from(label);
  const lines: string[] = [];
  for (let i = 0; i < chars.length; i += max) {
    lines.push(chars.slice(i, i + max).join(""));
  }
  return lines;
};

export default function CharacterNetworkView({ data, onChange }: Props) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // 计算节点布局
  const { nodes, edges } = useMemo(() => {
    const nodeList: Node[] = [];
    const usedNames = new Set<string>();

    // 1. 主角 (左侧中心)
    if (data.protagonist) {
      nodeList.push({
        id: data.protagonist.name || "主角",
        x: 180,
        y: CANVAS_HEIGHT / 2,
        data: data.protagonist,
        type: "protagonist",
      });
      usedNames.add(data.protagonist.name || "主角");
    }

    // 2. 反派 (右侧中心)
    if (data.antagonist) {
      nodeList.push({
        id: data.antagonist.name || "反派",
        x: CANVAS_WIDTH - 180,
        y: CANVAS_HEIGHT / 2,
        data: data.antagonist,
        type: "antagonist",
      });
      usedNames.add(data.antagonist.name || "反派");
    }

    // 3. 配角 (分布在上下圆弧)
    const supports = data.supporting_characters || [];
    if (supports.length > 0) {
      // 将配角分为上下两组
      const topGroup = supports.filter((_, i) => i % 2 === 0);
      const bottomGroup = supports.filter((_, i) => i % 2 === 1);

      // 上半圆弧
      topGroup.forEach((char, i) => {
        const step = CANVAS_WIDTH / (topGroup.length + 1);
        nodeList.push({
          id: char.name || `配角${i}`,
          x: step * (i + 1),
          y: 130, // 上方更远
          data: char,
          type: "support",
        });
        usedNames.add(char.name || `配角${i}`);
      });

      // 下半圆弧
      bottomGroup.forEach((char, i) => {
        const step = CANVAS_WIDTH / (bottomGroup.length + 1);
        nodeList.push({
          id: char.name || `配角${i}`,
          x: step * (i + 1),
          y: CANVAS_HEIGHT - 130, // 下方更远
          data: char,
          type: "support",
        });
        usedNames.add(char.name || `配角${i}`);
      });
    }

    // 4. 计算连线
    const edgeList: Array<{ x1: number; y1: number; x2: number; y2: number; label?: string }> = [];
    
    nodeList.forEach((source) => {
      const rels = source.data.relationships || {};
      const relsBrief = source.data.relationships_brief || {};
      Object.entries(rels).forEach(([targetName]) => {
        const target = nodeList.find((n) => n.data.name === targetName);
        if (target) {
          // 优先使用 relationships_brief，若无则回退到 relationships
          const label = relsBrief[targetName] || rels[targetName];
          edgeList.push({
            x1: source.x,
            y1: source.y,
            x2: target.x,
            y2: target.y,
            label,
          });
        }
      });
    });

    return { nodes: nodeList, edges: edgeList };
  }, [data]);

  const handleUpdateCharacter = (field: keyof Character, value: any) => {
    if (!selectedNode) return;

    const updatedChar = { ...selectedNode.data, [field]: value };
    const newData = { ...data };

    if (selectedNode.type === "protagonist") {
      newData.protagonist = updatedChar;
    } else if (selectedNode.type === "antagonist") {
      newData.antagonist = updatedChar;
    } else {
      // 配角
      const idx = (data.supporting_characters || []).findIndex(
        (c) => c.name === selectedNode.data.name
      );
      if (idx !== -1 && newData.supporting_characters) {
        newData.supporting_characters[idx] = updatedChar;
      }
    }

    onChange(newData);
    
    // 更新选中节点状态
    setSelectedNode({ ...selectedNode, data: updatedChar });
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((prev) => {
      const next = Math.min(2, Math.max(0.5, prev + delta));
      return Number(next.toFixed(2));
    });
  };

  const startPan = (e: React.MouseEvent<HTMLDivElement>) => {
    // 避免在点击节点时触发拖拽
    if ((e.target as HTMLElement).closest(".node-card")) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const onPan = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPanning) return;
    setOffset({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  };

  const endPan = () => setIsPanning(false);

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  return (
    <div className="relative h-full min-h-[500px] w-full select-none overflow-hidden rounded-xl border border-slate-200 bg-slate-50/50">
      {/* 缩放控件 */}
      <div className="absolute right-3 top-3 z-30 flex flex-col gap-2 rounded-xl bg-white/90 p-2 shadow-md">
        <button
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
          onClick={() => setScale((s) => Math.min(2, Number((s + 0.1).toFixed(2))))}
          aria-label="放大"
        >
          +
        </button>
        <button
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
          onClick={() => setScale((s) => Math.max(0.5, Number((s - 0.1).toFixed(2))))}
          aria-label="缩小"
        >
          −
        </button>
        <button
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100"
          onClick={resetView}
          aria-label="重置"
        >
          ⟳
        </button>
      </div>

      <div
        className="absolute inset-0"
        onWheel={handleWheel}
        onMouseDown={startPan}
        onMouseMove={onPan}
        onMouseUp={endPan}
        onMouseLeave={endPan}
        style={{ cursor: isPanning ? "grabbing" : "grab" }}
      >
        <div
          className="relative h-full w-full"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            transformOrigin: "0 0",
            width: CANVAS_WIDTH,
            height: CANVAS_HEIGHT,
          }}
        >
          {/* 连线层 (SVG) */}
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox={`0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#cbd5e1" />
              </marker>
            </defs>
            {edges.map((edge, i) => {
              const midX = (edge.x1 + edge.x2) / 2;
              const midY = (edge.y1 + edge.y2) / 2;
              const labelLines = wrapLabel(edge.label);
              const totalHeight = labelLines.length * 14;
              const startY = midY - totalHeight / 2;
              return (
                <g key={i}>
                  <line
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    stroke="#cbd5e1"
                    strokeWidth="2"
                    markerEnd="url(#arrowhead)"
                  />
                  {labelLines.map((line, idx) => (
                    <text
                      key={idx}
                      x={midX}
                      y={startY + idx * 14}
                      fontSize="11"
                      fill="#475569"
                      textAnchor="middle"
                      className="pointer-events-none"
                      style={{ paintOrder: "stroke", stroke: "white", strokeWidth: 3 }}
                    >
                      {line}
                    </text>
                  ))}
                </g>
              );
            })}
          </svg>

          {/* 节点层 */}
          <div className="absolute inset-0">
            {nodes.map((node) => (
              <div
                key={node.id}
                onClick={() => {
                  setSelectedNode(node);
                  setIsEditing(true);
                }}
                className={clsx(
                  "node-card absolute flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border p-3 shadow-sm transition-all hover:scale-105 hover:shadow-md",
                  node.type === "protagonist" && "border-blue-200 bg-blue-50 text-blue-900",
                  node.type === "antagonist" && "border-red-200 bg-red-50 text-red-900",
                  node.type === "support" && "border-slate-200 bg-white text-slate-900",
                  "hover:z-10"
                )}
                style={{
                  left: `${(node.x / CANVAS_WIDTH) * 100}%`,
                  top: `${(node.y / CANVAS_HEIGHT) * 100}%`,
                  width: NODE_WIDTH,
                  height: NODE_HEIGHT,
                  marginLeft: -NODE_WIDTH / 2,
                  marginTop: -NODE_HEIGHT / 2,
                }}
              >
                <div
                  className={clsx(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                    node.type === "protagonist" && "bg-blue-200 text-blue-700",
                    node.type === "antagonist" && "bg-red-200 text-red-700",
                    node.type === "support" && "bg-slate-200 text-slate-700"
                  )}
                >
                  {node.data.name?.slice(0, 1) || "?"}
                </div>
                <div className="text-center">
                  <div className="text-sm font-bold leading-tight">{node.data.name}</div>
                  <div className="text-[10px] opacity-70">{node.data.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 详情编辑弹窗 */}
      {isEditing && selectedNode && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-900/20 backdrop-blur-sm p-8">
          <div className="flex h-full max-h-[600px] w-full max-w-2xl flex-col rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/5 overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-800">
                编辑角色：{selectedNode.data.name}
                <span className={clsx("ml-2 rounded-full px-2 py-0.5 text-xs font-normal", 
                  selectedNode.type === "protagonist" ? "bg-blue-100 text-blue-700" :
                  selectedNode.type === "antagonist" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700"
                )}>
                  {selectedNode.type === "protagonist" ? "主角" : selectedNode.type === "antagonist" ? "反派" : "配角"}
                </span>
              </h3>
              <button 
                onClick={() => setIsEditing(false)}
                className="rounded-full p-1 hover:bg-slate-100 text-slate-500"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500">姓名</label>
                  <input 
                    className="input-field mt-1 w-full" 
                    value={selectedNode.data.name || ""} 
                    onChange={(e) => handleUpdateCharacter("name", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500">角色定位</label>
                  <input 
                    className="input-field mt-1 w-full" 
                    value={selectedNode.data.role || ""} 
                    onChange={(e) => handleUpdateCharacter("role", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500">性别</label>
                  <input 
                    className="input-field mt-1 w-full" 
                    value={selectedNode.data.gender || ""} 
                    onChange={(e) => handleUpdateCharacter("gender", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500">年龄</label>
                  <input 
                    className="input-field mt-1 w-full" 
                    type="number"
                    value={selectedNode.data.age || ""} 
                    onChange={(e) => handleUpdateCharacter("age", parseInt(e.target.value) || undefined)}
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500">外貌特征</label>
                <textarea 
                  className="input-field mt-1 w-full h-20 resize-none" 
                  value={selectedNode.data.appearance || ""} 
                  onChange={(e) => handleUpdateCharacter("appearance", e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500">性格特点</label>
                <textarea 
                  className="input-field mt-1 w-full h-20 resize-none" 
                  value={selectedNode.data.personality || ""} 
                  onChange={(e) => handleUpdateCharacter("personality", e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500">背景故事</label>
                <textarea 
                  className="input-field mt-1 w-full h-24 resize-none" 
                  value={selectedNode.data.background || ""} 
                  onChange={(e) => handleUpdateCharacter("background", e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500">行动动机</label>
                <textarea 
                  className="input-field mt-1 w-full h-16 resize-none" 
                  value={selectedNode.data.motivation || ""} 
                  onChange={(e) => handleUpdateCharacter("motivation", e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100">
               <button 
                onClick={() => setIsEditing(false)}
                className="btn-primary px-6"
              >
                完成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
