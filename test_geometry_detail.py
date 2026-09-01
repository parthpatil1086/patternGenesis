import io, json, cv2, numpy as np
from urllib.request import Request, urlopen

# Create synthetic test image with clear geometric primitives
img = np.full((500, 500, 3), 255, dtype=np.uint8)

# Draw concentric circles
for radius in [40, 80, 120]:
    cv2.circle(img, (250, 250), radius, (0, 0, 0), 2)

# Draw crossing lines (star pattern)
cv2.line(img, (250, 100), (250, 400), (0, 0, 0), 2)  # vertical
cv2.line(img, (100, 250), (400, 250), (0, 0, 0), 2)  # horizontal
cv2.line(img, (130, 130), (370, 370), (0, 0, 0), 2)  # diagonal 1
cv2.line(img, (370, 130), (130, 370), (0, 0, 0), 2)  # diagonal 2

ok, buffer = cv2.imencode('.png', img)
png_bytes = buffer.tobytes()

boundary = '----FormBoundary'
body = b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n' + png_bytes + b'\r\n--' + boundary.encode() + b'--\r\n'

req = Request(
    'http://127.0.0.1:8000/api/reconstruct',
    data=body,
    method='POST',
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

with urlopen(req, timeout=30) as res:
    data = json.load(res)
    geom = data.get('geometry', {})
    print("Geometry summary:")
    print(f"  Circles in response: {len(geom.get('circles', []))}")
    if geom.get('circles'):
        print(f"  First 3 circles: {[{'center': c.get('center'), 'radius': round(c.get('radius', 0), 1)} for c in geom.get('circles', [])[:3]]}")
    print(f"  Lines: {len(geom.get('lines', []))}")
    print(f"  Curves: {len(geom.get('bezier_curves', []))}")
    print(f"  Points: {len(geom.get('points', []))}")
    print(f"\nAnalysis section present: {'analysis' in data}")
    analysis = data.get('analysis', {})
    print(f"  Raw circles in analysis: {len(analysis.get('geometry', {}).get('circles', []))}")
