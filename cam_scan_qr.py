import os, sys
import cv2 # Install opencv-python
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import time
import my_common as my

RES_WIDTH = 1280
RES_HEIGHT = 720
BOUDING_BOX_COLOR = (0, 255, 0)  # Green color for bounding box
CHR_ABORT = 'q'

def scan_qr(cap):
    ret = None

    if not cap.isOpened():
        print(my.S_ERROR + "Could not open camera.")
        return None
    print("✅ Webcam opened. Point a QR code at the camera.")
    print(f"   Press '{CHR_ABORT}' in the camera window to quit.")

    while True:
        # Capture frame-by-frame
        success, frame = cap.read()
        if not success:
            print(my.ERROR + "Failed to capture frame.")
            return ret

        # Decode QR codes
        decoded_objects = decode(frame, symbols=[ZBarSymbol.QRCODE])

        for obj in decoded_objects:
            # Get the QR code data
            decoded_data = obj.data.decode('utf-8')

            # Draw a bounding box around the QR code
            points = obj.polygon
            if len(points) == 4:
                pts = [(points[i].x, points[i].y) for i in range(4)]
                cv2.polylines(frame, [np.array(pts)], True, BOUDING_BOX_COLOR, 3)

            # Print the data if it's new
            if decoded_data != ret:
                ret = decoded_data
                print(f"\n✅ QR Code Detected!")
                print(f"   Data: {ret}")

        # Display the resulting frame
        cv2.imshow('QR Code Scanner', frame)

        # Exit loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord(CHR_ABORT) or ret:
            break
    return ret

def init_capture(dev_idx=0):
    try:
        cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(my.S_ERROR + f"Could not open capture device {dev_idx}.")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RES_HEIGHT)
    except Exception as e:
        print(my.S_ERROR + str(e))
        return None
    return cap

def destroy_windows(cap = None):
    if cap:
        cap.release()
    cv2.destroyAllWindows()

def wrapper(args):
    ret = None
    if args and len(args) > 1:
        dev_idx = int(args[1])
    else:
        dev_idx = 0
    try:
        # Initialize the webcam. 0 is usually the default built-in camera.
        cap = init_capture(dev_idx)
        ret = scan_qr(cap)
        # When everything is done, release the capture and destroy windows
        destroy_windows(cap)
        print("\n👋 Webcam closed. Exiting.")
    except Exception as e:
        print(my.S_ERROR + str(e))
    return ret

if __name__ == "__main__":
    # start_at = datetime.datetime.now()

    # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # data_dir = BASE_DIR + "/data/qr"
    # my.mkdir(data_dir, True)
    # date = my.get_datetime()
    # filepath = "qr_" + date + ".txt"
    # filepath = data_dir + "/" + filepath

    ret = wrapper(sys.argv)
    print(ret)
    # my.save(ret, filepath)

    # finish_at = datetime.datetime.now()
    # print(f"Elapsed time: {finish_at - start_at}")
