import { imageFileUrl } from './api'
import MaskOverlay from './MaskOverlay'

// Image with the mask overlay stacked exactly on top of it.
export default function ImageViewer({ detail, categoryNames }) {
  const { image, objects } = detail
  return (
    <div className="viewer">
      <img src={imageFileUrl(image.id)} alt={image.file_name} />
      <MaskOverlay image={image} objects={objects} categoryNames={categoryNames} />
    </div>
  )
}
