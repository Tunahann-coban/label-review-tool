# Kontrol: ilk fotoğraf, paketteki çokgenlerle (yeşil: nesne, sarı kesik: aday)
import json, cv2
from IPython.display import Image as IPImage, FileLink, display

pkg = json.load(open(f"{OUT_DIR}/annotations.json", encoding="utf-8"))
first = pkg["images"][0]
img = cv2.imread(f"{OUT_DIR}/images/{first['file_name']}")
names = {c["id"]: c["name"] for c in pkg["categories"]}
for a in [a for a in pkg["annotations"] if a["image_id"] == first["id"]]:
    for poly in a["segmentation"]:
        pts = np.array(poly, np.int32).reshape(-1, 2)
        cv2.polylines(img, [pts], True, (0, 200, 0), 3)
        cv2.putText(img, f"{names[a['category_id']]} {a['score']:.2f}", tuple(pts.min(0)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 0), 2)
for c in [c for c in pkg["candidates"] if c["image_id"] == first["id"]]:
    for poly in c["segmentation"]:
        cv2.polylines(img, [np.array(poly, np.int32).reshape(-1, 2)], True, (0, 220, 255), 2)
cv2.imwrite("/kaggle/working/check_first_image.jpg", img)
display(IPImage("/kaggle/working/check_first_image.jpg", width=900))

# İndir: aşağıdaki bağlantıya tıkla (ya da sağ panel → Output → bidvision_package.zip → indir)
display(FileLink("bidvision_package.zip"))
