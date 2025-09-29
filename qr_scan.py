import cv2
import numpy as np
from pyzbar.pyzbar import decode
import time

def read_qr_fr_cam():
    """
    Initializes the webcam, detects and decodes QR codes,
    and displays the output.
    """
    # Initialize the webcam. 0 is usually the default built-in camera.
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        return

    print("✅ Webcam opened. Point a QR code at the camera.")
    print("   Press 'q' in the camera window to quit.")

    qr_data_found = None

    while True:
        # Capture frame-by-frame
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame.")
            break

        # Decode QR codes
        decoded_objects = decode(frame)

        for obj in decoded_objects:
            # Get the QR code data
            qr_data = obj.data.decode('utf-8')

            # Draw a bounding box around the QR code
            points = obj.polygon
            if len(points) == 4:
                pts = [(points[i].x, points[i].y) for i in range(4)]
                cv2.polylines(frame, [np.array(pts)], True, (0, 255, 0), 3)

            # Print the data if it's new
            if qr_data != qr_data_found:
                qr_data_found = qr_data
                print(f"\n✅ QR Code Detected!")
                print(f"   Data: {qr_data_found}")

        # Display the resulting frame
        cv2.imshow('QR Code Scanner', frame)

        # Exit loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything is done, release the capture and destroy windows
    cap.release()
    cv2.destroyAllWindows()
    print("\n👋 Webcam closed. Exiting.")

if __name__ == "__main__":
    # Import numpy here as it's only used for drawing the polygon

    read_qr_fr_cam()
