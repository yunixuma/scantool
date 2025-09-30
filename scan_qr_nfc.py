import os, sys
import datetime, time
import my_common as my
import cv2
import nfc
import nfc_scan
import cam_scan_qr
import myenclib

def scan_qr_nfc(cap, clf, key=None):
    try:
        qr_data = cam_scan_qr.scan_qr(cap)
        if key:
            nonce, ciphertext = myenclib.aesgcm_dec_b64(qr_data)
            name = myenclib.aesgcm_dec(key, nonce, ciphertext)
        else:
            name = qr_data
    except Exception as e:
        my.perror(e)
        name = qr_data
    print(f"Name: {name}")
    try:
        idm = nfc_scan.read_id(clf)
    except Exception as e:
        my.perror(e)
        idm = None
    print(f"IDm : {idm}")
    return { "name": name, "idm": idm }

def wrapper(args):
    ret = []
    if args and len(args) > 1 and len(args[1]) >= 16:
        key = myenclib.b64_dec(args[1])
    else:
        key = None
    if args and len(args) > 2:
        dev_idx = int(args[1])
    else:
        dev_idx = 0
    try:
        clf = nfc.ContactlessFrontend('usb')
        cap = cam_scan_qr.init_capture(dev_idx=0)
        while True:
            entry = scan_pair(cap, clf, key)
            ret.append(entry)
        clf.close()
        cam_scan_qr.destroy_windows(cap)
        cv2.destroyAllWindows()
    except Exception as e:
        print(my.S_ERROR + str(e))
    return ret

if __name__ == "__main__":
    # start_at = datetime.datetime.now()

    # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # data_dir = BASE_DIR + "/data/nfc"
    # my.mkdir(data_dir, True)
    # date = my.get_datetime()
    # filepath = "nfc_" + date + ".csv"
    # filepath = data_dir + "/" + filepath

    ret = wrapper(sys.argv)
    print(ret)
    # my.save_csv(ret, filepath)

    # finish_at = datetime.datetime.now()
    # print(f"Elapsed time: {finish_at - start_at}")
