// Shows what the last export wrote, or why it failed.
export default function ExportResult({ result, error, onClose }) {
  return (
    <div className="export-result" role="dialog" aria-label="Dışa aktarma sonucu">
      <div className="export-head">
        <b>{error ? 'Dışa aktarılamadı' : 'Dışa aktarıldı'}</b>
        <button onClick={onClose} aria-label="Kapat">✕</button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <p>
            <b>{result.images}</b> resim, <b>{result.objects}</b> nesne
            {result.empty_images > 0 && <> · {result.empty_images} resim nesnesiz (boş etiket dosyası)</>}
          </p>
          <p className="muted path">{result.path}</p>

          <table>
            <thead><tr><th>no</th><th>sınıf</th><th>nesne</th></tr></thead>
            <tbody>
              {result.per_class.map((c) => (
                <tr key={c.index} className={c.count === 0 ? 'muted' : ''}>
                  <td>{c.index}</td><td>{c.name}</td><td>{c.count}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {result.warnings.length > 0 && (
            <>
              <p><b>Uyarılar ({result.warnings.length})</b></p>
              <ul className="warnings">
                {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  )
}
