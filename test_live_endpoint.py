import io, json, cv2, numpy as np
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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

# Save to bytes
ok, buffer = cv2.imencode('.png', img)
png_bytes = buffer.tobytes()

# Send to backend
boundary = '----FormBoundary'
body = b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n' + png_bytes + b'\r\n--' + boundary.encode() + b'--\r\n'

req = Request(
    'http://127.0.0.1:8000/api/reconstruct',
    data=body,
    method='POST',
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

try:
    with urlopen(req, timeout=30) as res:
        data = json.load(res)
        print(f"✓ Status: {res.status}")
        print(f"✓ Has SVG: {'<svg' in data.get('reconstructed_svg','').lower()}")
        print(f"✓ Circles: {len(data.get('geometry', {}).get('circles', []))}")
        print(f"✓ Lines: {len(data.get('geometry', {}).get('lines', []))}")
        print(f"✓ Curves: {len(data.get('geometry', {}).get('bezier_curves', []))}")
        print(f"✓ Points: {len(data.get('geometry', {}).get('points', []))}")
        print(f"✓ Response keys: {list(data.keys())}")
except (HTTPError, URLError) as e:
    print(f"✗ Request failed: {e}")
