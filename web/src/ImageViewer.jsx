import { imageFileUrl } from './api'
import MaskOverlay from './MaskOverlay'

// Image with the mask overlay stacked exactly on top of it.
// candidates: list to draw, or null when candidates are hidden.
export default function ImageViewer({ detail, categoryNames, selectedId, onSelect,
  candidates, selectedCandidateId, onSelectCandidate }) {
  const { image, objects } = detail
  return (
    <div className="viewer">
      <img src={imageFileUrl(image.id)} alt={image.file_name} />
      <MaskOverlay image={image} objects={objects} categoryNames={categoryNames}
        selectedId={selectedId} onSelect={onSelect}
        candidates={candidates} selectedCandidateId={selectedCandidateId}
        onSelectCandidate={onSelectCandidate} />
    </div>
  )
}
