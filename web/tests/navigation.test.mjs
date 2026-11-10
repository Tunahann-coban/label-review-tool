// Checks for src/navigation.js. Run: npm test
import { countByGroup, findNextPending, inGroup, moveInGroup } from '../src/navigation.js'

let fail = 0
const check = (name, cond) => { console.log(cond ? 'OK  ' : 'FAIL', name); if (!cond) fail++ }
// p = pending, r = done (tamamlandı), e = pending + on the edit list, d = done + on the edit list
const MARKS = {
  p: { status: 'pending', needs_edit: false },
  r: { status: 'reviewed', needs_edit: false },
  e: { status: 'pending', needs_edit: true },
  d: { status: 'reviewed', needs_edit: true },
}
const imgs = (marks) => marks.split('').map((s) => ({ ...MARKS[s] }))

check('next pending ahead', findNextPending(imgs('rppp'), 0) === 1)
check('skips done ones', findNextPending(imgs('prrp'), 0) === 3)
check('current pending image is not "next"', findNextPending(imgs('pppp'), 1) === 2)
check('wraps to the start', findNextPending(imgs('prrr'), 2) === 0)
check('finds a skipped image behind', findNextPending(imgs('rprr'), 3) === 1)
check('only current pending -> null', findNextPending(imgs('rrpr'), 2) === null)
check('all done -> null', findNextPending(imgs('rrrr'), 0) === null)
check('single image -> null', findNextPending(imgs('p'), 0) === null)
check('empty package -> null', findNextPending([], 0) === null)
check('on the edit list but unfinished is still pending', findNextPending(imgs('peer'), 0) === 1)
check('done and on the edit list is finished', findNextPending(imgs('pddr'), 0) === null)

check('group "all" holds everything', imgs('predp').every((i) => inGroup(i, 'all')))
check('pending group: unfinished, flagged or not',
  inGroup(MARKS.p, 'pending') && inGroup(MARKS.e, 'pending') && !inGroup(MARKS.r, 'pending') && !inGroup(MARKS.d, 'pending'))
check('done group: finished, flagged or not',
  inGroup(MARKS.r, 'reviewed') && inGroup(MARKS.d, 'reviewed') && !inGroup(MARKS.p, 'reviewed'))
check('edit group: flagged, finished or not',
  inGroup(MARKS.e, 'needs_edit') && inGroup(MARKS.d, 'needs_edit') && !inGroup(MARKS.r, 'needs_edit'))
check('an image without the flag field counts as not flagged', !inGroup({ status: 'reviewed' }, 'needs_edit'))
const c = countByGroup(imgs('pprrdee'))
check('counts per group (one image can be in two groups)',
  c.all === 7 && c.pending === 4 && c.reviewed === 3 && c.needs_edit === 3)
check('counts of an empty package', countByGroup([]).all === 0 && countByGroup([]).needs_edit === 0)

check('next inside the group skips other images', moveInGroup(imgs('epepe'), 'needs_edit', 0, 1) === 2)
check('previous inside the group', moveInGroup(imgs('epepe'), 'needs_edit', 4, -1) === 2)
check('stops at the end of the group', moveInGroup(imgs('epepe'), 'needs_edit', 4, 1) === 4)
check('stops at the start of the group', moveInGroup(imgs('epepe'), 'needs_edit', 0, -1) === 0)
check('group all moves one by one', moveInGroup(imgs('epepe'), 'all', 1, 1) === 2)
check('current image left the group: forward -> first of the group', moveInGroup(imgs('rprpr'), 'pending', 0, 1) === 1)
check('current image left the group: back -> last of the group', moveInGroup(imgs('rprpr'), 'pending', 4, -1) === 3)
check('empty group -> stay', moveInGroup(imgs('rrr'), 'needs_edit', 1, 1) === 1)

console.log(fail ? `${fail} failed` : 'all passed')
process.exit(fail ? 1 : 0)
