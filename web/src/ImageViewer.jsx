import { imageFileUrl } from './api'
import MaskOverlay from './MaskOverlay'

// Image with the mask overlay stacked exactly on top of it, scaled up or down to fill
// the stage. The CSS reads --ar (width / height) to keep the photo's shape and uses the
// room the stage has (viewer-box is a size container, see index.css).
// header: what sits above the photo inside the same card (the navigation bar).
// candidates: list to draw, or null when candidates are hidden.
export default function ImageViewer({ detail, categoryNames, selectedId, onSelect,
  candidates, selectedCandidateId, onSelectCandidate, view, header }) {
  const { image, objects } = detail
  return (
    <div className="stage">
      {header}
      <div className="viewer-box">
        <div className="viewer" style={{ '--ar': image.width / image.height }}>
          <img src={imageFileUrl(image.id)} alt={image.file_name} />
          <MaskOverlay image={image} objects={objects} categoryNames={categoryNames}
            selectedId={selectedId} onSelect={onSelect}
            candidates={candidates} selectedCandidateId={selectedCandidateId}
            onSelectCandidate={onSelectCandidate} view={view} />
        </div>
      </div>
    </div>
  )
}
