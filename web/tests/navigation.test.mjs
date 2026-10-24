// Checks for src/navigation.js. Run: npm test
import { findNextPending } from '../src/navigation.js'

let fail = 0
const check = (name, cond) => { console.log(cond ? 'OK  ' : 'FAIL', name); if (!cond) fail++ }
const imgs = (statuses) => statuses.split('').map((s) => ({ status: s === 'r' ? 'reviewed' : 'pending' }))

check('next pending ahead', findNextPending(imgs('rppp'), 0) === 1)
check('skips reviewed ones', findNextPending(imgs('prrp'), 0) === 3)
check('current pending image is not "next"', findNextPending(imgs('pppp'), 1) === 2)
check('wraps to the start', findNextPending(imgs('prrr'), 2) === 0)
check('finds a skipped image behind', findNextPending(imgs('rprr'), 3) === 1)
check('only current pending -> null', findNextPending(imgs('rrpr'), 2) === null)
check('all reviewed -> null', findNextPending(imgs('rrrr'), 0) === null)
check('single image -> null', findNextPending(imgs('p'), 0) === null)
check('empty package -> null', findNextPending([], 0) === null)

console.log(fail ? `${fail} failed` : 'all passed')
process.exit(fail ? 1 : 0)
