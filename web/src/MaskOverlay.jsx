import { objectColor } from './colors'
import { objectAt } from './geometry'

// [x1, y1, x2, y2, ...] -> "x1,y1 x2,y2 ..."
function toPoints(flat) {
  const pairs = []
  for (let i = 0; i + 1 < flat.length; i += 2) pairs.push(`${flat[i]},${flat[i + 1]}`)
  return pairs.join(' ')
}

// Label goes just above the bbox; if there is no room, just inside it.
function labelPosition(bbox, fontSize, width) {
  const [x, y] = bbox
  const top = y - fontSize * 0.3
  return {
    x: Math.min(Math.max(x, 2), width - 2),
    y: top < fontSize ? y + fontSize : top,
  }
}

// Screen click -> image pixel coordinates, whatever the on-screen size.
function toImagePoint(svg, clientX, clientY) {
  const pt = svg.createSVGPoint()
  pt.x = clientX
  pt.y = clientY
  return pt.matrixTransform(svg.getScreenCTM().inverse())
}

/**
 * Draws masks on top of the image. Uses image pixel coordinates via viewBox,
 * so the browser handles scaling to the on-screen size.
 *
 * view: 'fill' (tinted masks), 'outline' (edges only, the photo stays visible),
 *       'hidden' (raw photo; only the selected object's edge). Clicking works the
 *       same in every view: it uses the shapes, not what is on screen.
 */
export default function MaskOverlay({ image, objects, categoryNames, selectedId, onSelect,
  candidates, selectedCandidateId, onSelectCandidate, view = 'fill' }) {
  const { width, height } = image
  const fontSize = Math.max(12, Math.round(width / 50))

  // Color follows the object's position in the package, not the draw order.
  // Deleted objects are not drawn and cannot be clicked on the image.
  const items = objects
    .map((obj, i) => ({ obj, color: objectColor(i) }))
    .filter((it) => it.obj.state !== 'deleted')
  const visible = items.map((it) => it.obj)
  // Selected object is drawn last so it sits on top.
  const ordered = [
    ...items.filter((it) => it.obj.id !== selectedId),
    ...items.filter((it) => it.obj.id === selectedId),
  ]
  const drawn = view === 'hidden' ? ordered.filter((it) => it.obj.id === selectedId) : ordered

  // With candidates shown, a click looks for a candidate first, so one lying
  // under an existing mask can still be picked.
  const handleClick = (e) => {
    const p = toImagePoint(e.currentTarget, e.clientX, e.clientY)
    const cand = candidates && objectAt(p.x, p.y, candidates)
    if (cand) onSelectCandidate(cand.id)
    else onSelect(objectAt(p.x, p.y, visible)?.id ?? null)
  }

  return (
    <svg className="overlay" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
      onClick={handleClick}>
      {drawn.map(({ obj, color }) => {
        const selected = obj.id === selectedId
        const name = categoryNames[obj.category_id] ?? `#${obj.category_id}`
        const label = obj.score != null ? `${name} ${obj.score.toFixed(2)}` : name
        const pos = labelPosition(obj.bbox, fontSize, width)
        return (
          <g key={obj.id} className={selected ? 'mask selected' : 'mask'}>
            {obj.segmentation.map((poly, k) => (
              <polygon key={k} points={toPoints(poly)} fill={color}
                fillOpacity={view !== 'fill' ? 0 : selected ? 0.5 : 0.35}
                stroke={selected ? '#fff' : color} strokeWidth={selected ? 5 : view === 'outline' ? 2.5 : 2}
                vectorEffect="non-scaling-stroke" />
            ))}
            {selected && obj.segmentation.map((poly, k) => (
              <polygon key={`edge-${k}`} points={toPoints(poly)} fill="none"
                stroke={color} strokeWidth={3} vectorEffect="non-scaling-stroke" />
            ))}
            {view !== 'hidden' && (
              <text x={pos.x} y={pos.y} fontSize={fontSize} className="mask-label">{label}</text>
            )}
          </g>
        )
      })}
      {candidates?.map((cand) => {
        const selected = cand.id === selectedCandidateId
        return (
          <g key={`cand-${cand.id}`} className={selected ? 'candidate selected' : 'candidate'}>
            {cand.segmentation.map((poly, k) => (
              <g key={k}>
                {/* black under white dashes: visible on light and dark backgrounds */}
                <polygon points={toPoints(poly)} fill={selected ? '#ffd400' : 'none'} fillOpacity={0.35}
                  stroke="#000" strokeWidth={selected ? 4 : 3} vectorEffect="non-scaling-stroke" />
                <polygon points={toPoints(poly)} fill="none" stroke={selected ? '#ffd400' : '#fff'}
                  strokeWidth={selected ? 2.5 : 1.5} strokeDasharray="6 4" vectorEffect="non-scaling-stroke" />
              </g>
            ))}
          </g>
        )
      })}
    </svg>
  )
}
