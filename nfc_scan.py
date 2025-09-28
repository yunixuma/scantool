import os, sys
import nfc
from nfc.clf import RemoteTarget
import binascii
import datetime, time
import my_common as my
import nfc_utils as nfcu

SENSE_INTERVAL = 1

def sense_target(clf, targets):
    rdwr_options = {
        'terminate_on_timeout': True,
        'timeout': nfcu.SENSE_INTERVAL,
    }
    target = clf.sense(
        *targets,
        rdwr=rdwr_options,
        interval=nfcu.SENSE_INTERVAL,
        timeout=nfcu.SENSE_TIMEOUT
        )
    if target is None:
        return None
    return nfc.tag.activate(clf, target)

def read_id(clf):
    uids = []
    while True:
        keys = list(nfcu.TARGET_CODES.keys())
        for key in keys:
            print("Scanning for {}".format(key))
            tag = sense_target(clf, nfcu.TARGET_CODES[key])
            if tag is None:
                continue
            print(f"{key} detected")
            if tag.type == 'Type3Tag':
                return tag.idm.hex().upper()
            else:
                uid = tag.identifier.hex().upper()
                if uid in uids:
                    return uid
                else:
                    uids.append(uid)
        time.sleep(SENSE_INTERVAL)

def wrapper(args):
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            uid = read_id(clf)
            return uid
    except IOError:
        print(my.S_ERROR + "Could not connect to RFID reader.")
        print(my.S_ERROR + "Please check the driver installation and device connection.")
    except KeyboardInterrupt:
        # This block is executed when Ctrl+C is pressed
        print("\n\n🛑 Ctrl+C detected. Exiting script.")
        # Perform any cleanup actions here if needed
        # For example: close files, save state, etc.
        sys.exit(0) # Exit the program cleanly
    except Exception as e:
        print(my.S_ERROR + str(e))

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
