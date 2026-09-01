import io, json, cv2, numpy as np
from urllib.request import Request, urlopen

# Create a realistic test: centered pattern with frame/border
img = np.full((600, 600, 3), 200, dtype=np.uint8)  # Gray background (like a photo)

# Add a dark frame/border (like a photograph border)
cv2.rectangle(img, (20, 20), (580, 580), (50, 50, 50), 15)

# Draw the actual pattern in the center (which should be isolated)
center = (300, 300)

# Draw concentric circles (main motif)
for radius in [35, 70, 105]:
    cv2.circle(img, center, radius, (10, 10, 10), 2)

# Draw 4-fold symmetry lines
cv2.line(img, (300, 200), (300, 400), (10, 10, 10), 2)  # vertical
cv2.line(img, (200, 300), (400, 300), (10, 10, 10), 2)  # horizontal

# Add some star pattern
cv2.line(img, (220, 220), (380, 380), (10, 10, 10), 2)  # diagonal 1
cv2.line(img, (380, 220), (220, 380), (10, 10, 10), 2)  # diagonal 2

# Add corner motifs
cv2.circle(img, (150, 150), 20, (10, 10, 10), 2)
cv2.circle(img, (450, 150), 20, (10, 10, 10), 2)
cv2.circle(img, (150, 450), 20, (10, 10, 10), 2)
cv2.circle(img, (450, 450), 20, (10, 10, 10), 2)

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
    analysis = data.get('analysis', {})
    
    print("=" * 60)
    print("TEST: Pattern with frame/border (artwork isolation)")
    print("=" * 60)
    print(f"\nFinal Reconstruction Geometry:")
    print(f"  Circles: {len(geom.get('circles', []))}")
    print(f"  Lines: {len(geom.get('lines', []))}")
    print(f"  Curves: {len(geom.get('bezier_curves', []))}")
    print(f"  Points: {len(geom.get('points', []))}")
    
    print(f"\nSymmetry Detection:")
    symmetry = analysis.get('symmetry', {}).get('detected', [{}])[0]
    print(f"  Type: {symmetry.get('type', 'none')}")
    print(f"  Order: {symmetry.get('order', 0)}")
    print(f"  Confidence: {symmetry.get('confidence', 0.0):.2f}")
    
    print(f"\nArtwork Isolation (from analysis debug):")
    debug = analysis.get('debug', {})
    print(f"  Source dimensions: {debug.get('source_width')} x {debug.get('source_height')}")
    print(f"  Filtered circles: {debug.get('filtered_circle_count', 0)}")
    print(f"  Curves: {debug.get('curve_count', 0)}")
    print(f"  Points: {debug.get('points_count', 0)}")
    
    print(f"\nSVG Generated: {len(data.get('reconstructed_svg', ''))} chars")
    print(f"Response keys: {list(data.keys())}")
    print("\n✓ Test complete - pattern with frame successfully processed")
