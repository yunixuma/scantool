import os, sys
import cv2
import numpy as np
import zxingcpp
import threading
import queue
import time

RES_WIDTH = 1280
RES_HEIGHT = 720
BOUDING_BOX_COLOR = (0, 255, 0)
CHR_ABORT = 'q'

# Global variable
# Queue for sharing frames inter threads
frame_queue = queue.Queue(maxsize=1) 
# Event to signal threads to stop
stop_event = threading.Event()
# decoded QR code result
qr_result = None

def decoder_thread():
    """Special thread for decoding QR codes using zxing-cpp"""
    global qr_result
    print("✅ Decoder thread started.")
    
    frame_skip = 2  # Process every 2nd frame to reduce CPU load
    frame_count = 0

    while not stop_event.is_set():
        try:
            # Retrieve the latest frame from the queue (waiting up to 0.1 sec)
            frame = frame_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        # Convert to grayscale as zxing-cpp works better on single channel images
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Decoding by zxing-cpp (specialized for QR codes)
        results = zxingcpp.read_barcodes(gray_frame, formats=zxingcpp.BarcodeFormat.QRCode)
        
        if results:
            qr_result = results[0] # Take the first detected QR code
            stop_event.set() # if success, signal to stop
            break
            
    print("👋 Decoder thread finished.")

# def main_thread(cap):
def scan_qr(cap):
    """Main thread for capturing frames and displaying them"""
    global qr_result, frame_queue, stop_event

    # Reset global state variables before starting a new scan
    qr_result = None
    stop_event.clear()
    # Clear the queue in case there's a leftover frame
    while not frame_queue.empty():
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            break

    # Starting the decoder thread
    dec_thread = threading.Thread(target=decoder_thread, daemon=True)
    dec_thread.start()
    
    print("✅ Webcam opened. Point a QR code at the camera.")
    print(f"   Press '{CHR_ABORT}' to quit.")
    
    start_time = time.time()
    
    while not stop_event.is_set():
        success, frame = cap.read()
        if not success:
            break

        # Sending the first frame to the retrieving frame thread
        if not frame_queue.full():
            frame_queue.put(frame)
            
        # Display the frame
        # cv2.imshow('QR Code Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord(CHR_ABORT):
            stop_event.set()
            break

    # Finalize
    dec_thread.join() # Wait for decoder thread to finish
    
    if qr_result:
        end_time = time.time()
        print("\n" + "="*30)
        print("🎉 QR Code Detected!")
        print(f"   Data: {qr_result.text}")
        print(f"   Detection Time: {end_time - start_time:.2f} seconds")
        print("="*30)
        
        # Display the bounding box on the last frame
        # final_frame = cv2.imread("temp_frame.jpg") # A bit of a hack to get the last good frame
        # if final_frame is not None:
        #     pos = qr_result.position
        #     pts = np.array([[pos.top_left.x, pos.top_left.y], 
        #                     [pos.top_right.x, pos.top_right.y], 
        #                     [pos.bottom_right.x, pos.bottom_right.y], 
        #                     [pos.bottom_left.x, pos.bottom_left.y]], dtype=np.int32)
        #     cv2.polylines(final_frame, [pts], True, BOUDING_BOX_COLOR, 3)
        #     cv2.imshow('QR Code Scanner', final_frame)
        #     cv2.waitKey(0) # Keep window open until a key is pressed

    else:
        print("\nQR Code not found or scan was aborted.")

    # A final cleanup for the temp file
    # if os.path.exists("temp_frame.jpg"):
    #     os.remove("temp_frame.jpg")
    return qr_result.text if qr_result else None

# A little hack to display the final result on the correct frame
def capture_and_display(cap, dec_thread):
    # This function will run in the main thread
    while not stop_event.is_set():
        success, frame = cap.read()
        if not success:
            stop_event.set()
            break

        if not frame_queue.full():
            frame_queue.put(frame.copy()) # Pass a copy to the decoder thread

        cv2.imshow('QR Code Scanner', frame)
        
        # Save the last frame for final display
        # cv2.imwrite("temp_frame.jpg", frame)

        if cv2.waitKey(1) & 0xFF == ord(CHR_ABORT):
            stop_event.set()
            break

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
