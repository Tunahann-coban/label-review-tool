// Distinct color per object: golden-angle hue steps keep neighbours far apart.
export function objectColor(index) {
  const hue = Math.round((index * 137.508) % 360)
  return `hsl(${hue} 85% 50%)`
}
