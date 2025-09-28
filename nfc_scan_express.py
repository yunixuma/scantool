import nfc
from nfc.clf import RemoteTarget
import time

def get_iphone_suica_idm(clf):
    """
    Polls for an iPhone's Suica and returns its IDm.
    """
    # 1. Create a specific polling command for Suica (System Code 0x0003)
    sensf_req_suica = bytearray.fromhex("000003010F")
    felica_target = RemoteTarget('212F', sensf_req=sensf_req_suica)

    # 2. Use clf.sense() to look only for this specific target
    target = clf.sense(felica_target, timeout=0.5)

    if target is None:
        return None

    # --- ▼▼▼ This is the key change ▼▼▼ ---
    try:
        # 3. Activate the tag. This is a crucial step.
        #    It identifies the tag and loads the correct module internally.
        tag = nfc.tag.activate(clf, target)

        # 4. Check the tag's '.type' attribute as a string.
        #    This is the most reliable way to identify the tag.
        if tag.type == 'Type3Tag':
            return tag.idm.hex().upper()
        else:
            # The target responded to a FeliCa poll but isn't a Type3Tag.
            # This is unlikely but handled just in case.
            print(f"WARN: FeliCa target responded but activated as {tag.type}")
            return None

    except Exception as e:
        print(f"ERROR: Failed to activate tag: {e}")
        return None
    # --- ▲▲▲ End of key change ▲▲▲ ---


if __name__ == "__main__":
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("✅ Reader detected. Please tap your iPhone with Suica enabled.")
            print("-" * 30)

            while True:
                idm = get_iphone_suica_idm(clf)

                if idm:
                    print(f"  ✅ Success! iPhone Suica IDm found:")
                    print(f"     IDm: {idm}")
                    print("-" * 30)
                    # Wait 3 seconds to avoid re-reading instantly
                    time.sleep(3)
                    print("\nPlease tap your iPhone again.")

                time.sleep(0.1)

    except IOError:
        print("❌ Could not connect to RFID reader.")
    except KeyboardInterrupt:
        print("\nScript terminated by user.")