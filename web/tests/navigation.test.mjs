// Checks for src/navigation.js. Run: npm test
import { countByGroup, findNextPending, inGroup, moveInGroup } from '../src/navigation.js'

let fail = 0
const check = (name, cond) => { console.log(cond ? 'OK  ' : 'FAIL', name); if (!cond) fail++ }
// p = pending, r = reviewed (tamamlandı), e = needs_edit (düzenlenecek)
const STATUS = { p: 'pending', r: 'reviewed', e: 'needs_edit' }
const imgs = (statuses) => statuses.split('').map((s) => ({ status: STATUS[s] }))

check('next pending ahead', findNextPending(imgs('rppp'), 0) === 1)
check('skips reviewed ones', findNextPending(imgs('prrp'), 0) === 3)
check('current pending image is not "next"', findNextPending(imgs('pppp'), 1) === 2)
check('wraps to the start', findNextPending(imgs('prrr'), 2) === 0)
check('finds a skipped image behind', findNextPending(imgs('rprr'), 3) === 1)
check('only current pending -> null', findNextPending(imgs('rrpr'), 2) === null)
check('all reviewed -> null', findNextPending(imgs('rrrr'), 0) === null)
check('single image -> null', findNextPending(imgs('p'), 0) === null)
check('empty package -> null', findNextPending([], 0) === null)
check('needs_edit images are not pending', findNextPending(imgs('peep'), 0) === 3)
check('only needs_edit left -> null', findNextPending(imgs('peer'), 0) === null)

check('group "all" holds everything', imgs('pre').every((i) => inGroup(i, 'all')))
check('group matches its status only', inGroup({ status: 'needs_edit' }, 'needs_edit') && !inGroup({ status: 'reviewed' }, 'needs_edit'))
const c = countByGroup(imgs('pprree'))
check('counts per group', c.all === 6 && c.pending === 2 && c.reviewed === 2 && c.needs_edit === 2)
check('counts of an empty package', countByGroup([]).all === 0 && countByGroup([]).needs_edit === 0)

check('next inside the group skips other statuses', moveInGroup(imgs('epepe'), 'needs_edit', 0, 1) === 2)
check('previous inside the group', moveInGroup(imgs('epepe'), 'needs_edit', 4, -1) === 2)
check('stops at the end of the group', moveInGroup(imgs('epepe'), 'needs_edit', 4, 1) === 4)
check('stops at the start of the group', moveInGroup(imgs('epepe'), 'needs_edit', 0, -1) === 0)
check('group all moves one by one', moveInGroup(imgs('epepe'), 'all', 1, 1) === 2)
check('current image left the group: forward -> first of the group', moveInGroup(imgs('repre'), 'pending', 0, 1) === 2)
check('current image left the group: back -> last of the group', moveInGroup(imgs('rprpr'), 'pending', 4, -1) === 3)
check('empty group -> stay', moveInGroup(imgs('rrr'), 'needs_edit', 1, 1) === 1)

console.log(fail ? `${fail} failed` : 'all passed')
process.exit(fail ? 1 : 0)
