import { useEffect, useRef } from 'react'
import { imageThumbUrl } from './api'
import { GROUPS, countByGroup, inGroup } from './navigation'
import { IMAGE_STATUS_LABELS } from './states'

// The "folders": pick a group (all / pending / done / needs edit) and see its images
// as a list. Any image can be opened and edited again, whichever group it is in.
// The files never move; a group is just a filter on the image's status.
export default function ImageList({ images, index, group, onGroup, onPick }) {
  const currentRef = useRef(null)
  const counts = countByGroup(images)
  const items = []
  images.forEach((img, i) => { if (inGroup(img, group)) items.push({ img, i }) })

  // keep the open image in view (also after "Next" or a click on the picture)
  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: 'nearest' })
  }, [index, group])

  return (
    <div className="object-list image-list">
      <div className="list-header">
        <div className="group-pills" role="group" aria-label="Resim grubu">
          {GROUPS.map((g) => (
            <button key={g.id} aria-pressed={group === g.id} onClick={() => onGroup(g.id)}
              className={group === g.id ? 'pill on' : 'pill'}>
              {g.label} <span className="pill-count">{counts[g.id]}</span>
            </button>
          ))}
        </div>
      </div>
      {items.length === 0 ? (
        <p className="muted empty-note">Bu grupta resim yok.</p>
      ) : (
        <ul>
          {items.map(({ img, i }) => (
            <li key={img.id} ref={i === index ? currentRef : null}
              className={i === index ? 'selected' : ''} onClick={() => onPick(i)}>
              <img className="thumb" src={imageThumbUrl(img.id)} alt="" loading="lazy" />
              <span className="name" title={img.file_name}>
                <span className="file">{img.file_name}</span>
                {img.status_by && <span className="by">{img.status_by}</span>}
              </span>
              <span className={`status status-${img.status}`}>{IMAGE_STATUS_LABELS[img.status]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
