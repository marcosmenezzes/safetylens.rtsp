import cv2
from core.detection import CameraCapture

# Replace with your DroidCam IP address
DROIDCAM_URL = "http://192.168.1.100:4747/video"

# Initialize camera with DroidCam URL
camera = CameraCapture(DROIDCAM_URL)

class CameraCapture:
    def __init__(self, camera_url=None):
        # If no camera_url is provided, it will use default webcam (0)
        if camera_url is None:
            self.camera_source = 0
        else:
            self.camera_source = camera_url
        
        self.cap = cv2.VideoCapture(self.camera_source)
        
    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        self.cap.release()