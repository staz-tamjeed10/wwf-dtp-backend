# camera_streams.py
import cv2
from pyzbar.pyzbar import decode

class CameraStream:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)

    def get_frames(self):
        while True:
            success, frame = self.camera.read()
            if not success:
                break

            for barcode in decode(frame):
                qr_data = barcode.data.decode("utf-8")
                print(f"Scanned QR Code: {qr_data}")

                # Optional: Stop the camera on successful scan
                self.camera.release()
                yield f"data: {qr_data}\n\n".encode()

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
