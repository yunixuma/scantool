import os, sys
import cv2
import time

RES_WIDTH = 1280
RES_HEIGHT = 720
BOUDING_BOX_COLOR = (0, 255, 0)
CHR_ABORT = 'q'

def init_capture(dev_idx=0):
    try:
        cap = cv2.VideoCapture(dev_idx)
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
