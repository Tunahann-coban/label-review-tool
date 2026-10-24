import { objectColor } from './colors'

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

/**
 * Draws masks on top of the image. Uses image pixel coordinates via viewBox,
 * so the browser handles scaling to the on-screen size.
 */
export default function MaskOverlay({ image, objects, categoryNames }) {
  const { width, height } = image
  const fontSize = Math.max(12, Math.round(width / 50))

  return (
    <svg className="overlay" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {objects.map((obj, i) => {
        const color = objectColor(i)
        const name = categoryNames[obj.category_id] ?? `#${obj.category_id}`
        const label = obj.score != null ? `${name} ${obj.score.toFixed(2)}` : name
        const pos = labelPosition(obj.bbox, fontSize, width)
        return (
          <g key={obj.id}>
            {obj.segmentation.map((poly, k) => (
              <polygon key={k} points={toPoints(poly)} fill={color} fillOpacity={0.35}
                stroke={color} strokeWidth={2} vectorEffect="non-scaling-stroke" />
            ))}
            <text x={pos.x} y={pos.y} fontSize={fontSize} className="mask-label">{label}</text>
          </g>
        )
      })}
    </svg>
  )
}
