// Checks for src/suspects.js. Run: npm test
import { orderObjects, suspectReasons, unknownCategoryIds } from '../src/suspects.js'
let fail = 0
const check = (name, cond) => { console.log(cond ? 'OK  ' : 'FAIL', name); if (!cond) fail++ }
const cats = [{ id: 1, name: 'box' }, { id: 2, name: 'tote' }, { id: 8, name: 'Unknown ' }]
const unk = unknownCategoryIds(cats)
check('unknown found by name, case/space-insensitive', unk.has(8) && unk.size === 1)
check('no unknown category -> empty set', unknownCategoryIds([{ id: 1, name: 'box' }]).size === 0)

const o = (id, score, category_id, extra = {}) => ({ id, score, category_id, state: 'auto', ...extra })
check('score below threshold', suspectReasons(o(1, 0.49, 1), 0.5, unk).length === 1)
check('score exactly at threshold is NOT suspect', suspectReasons(o(1, 0.5, 1), 0.5, unk).length === 0)
check('null score is not suspect by score', suspectReasons(o(1, null, 1), 0.5, unk).length === 0)
check('unknown with high score is suspect', suspectReasons(o(1, 0.95, 8), 0.5, unk)[0] === 'sınıf: unknown')
check('low score + unknown gives two reasons', suspectReasons(o(1, 0.1, 8), 0.5, unk).length === 2)
check('unknown changed to box stays suspect (stable list)',
  suspectReasons(o(1, 0.9, 1, { state: 'changed', orig_category_id: 8 }), 0.5, unk).length === 1)
check('box changed to unknown is not suspect by class',
  suspectReasons(o(1, 0.9, 8, { state: 'changed', orig_category_id: 1 }), 0.5, unk).length === 0)
check('threshold 0 -> nothing suspect by score', suspectReasons(o(1, 0.0, 1), 0, unk).length === 0)
check('threshold 1 -> everything below 1 suspect', suspectReasons(o(1, 0.99, 1), 1, unk).length === 1)

const objs = [o(10, 0.9, 1), o(11, 0.3, 2), o(12, 0.8, 8), o(13, 0.1, 1), o(14, 0.7, 2), o(15, null, 1)]
const ord = orderObjects(objs, 0.5, unk)
check('suspects first, lowest score first', ord.map((i) => i.obj.id).join() === '13,11,12,10,14,15')
check('color index = package position', ord.every((it) => objs[it.colorIndex] === it.obj))
check('all objects kept', ord.length === objs.length)
const ord2 = orderObjects(objs, 0.85, unk)
check('higher threshold pulls more up', ord2.map((i) => i.obj.id).join() === '13,11,14,12,10,15')
const accepted = objs.map((x) => (x.id === 11 ? { ...x, state: 'accepted' } : x))
check('accepting does not reorder', orderObjects(accepted, 0.5, unk).map((i) => i.obj.id).join() === ord.map((i) => i.obj.id).join())
console.log(fail ? `${fail} failed` : 'all passed'); process.exit(fail ? 1 : 0)
