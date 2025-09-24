import os
import sys
import nfc
import binascii
import time

# --- Key Change 1: Correctly build the FeliCa polling command ---
# [Command Code(0x00)][System Code(2 bytes, big-endian)][Request Code(0x01)][Time Slot(0x0F)]
FELICA_SYSTEM_CODE = 0xFE00
SENSF_REQ = bytearray([0x00]) + FELICA_SYSTEM_CODE.to_bytes(2, 'big') + bytearray([0x01, 0x0F])

def get_tag_info(tag):
    """A helper function to get a readable name for a tag."""
    if isinstance(tag, nfc.tag.Type1Tag):
        return "Topaz (Type 1)"
    elif isinstance(tag, nfc.tag.Type2Tag):
        return "MIFARE Ultralight (Type 2)"
    elif isinstance(tag, nfc.tag.Type3Tag):
        return "FeliCa (Type 3)"
    elif isinstance(tag, nfc.tag.Type4Tag):
        # Differentiate between Type A and B if possible
        if 'TypeA' in str(type(tag)):
            return "Type 4A"
        elif 'TypeB' in str(type(tag)):
            return "Type 4B"
        return "Type 4"
    elif isinstance(tag, nfc.tag.Type5Tag):
        return "ISO/IEC 15693 (Type 5)"
    else:
        return "Unknown Tag"

def on_connect(tag):
    """Callback function executed when a tag is connected."""
    tag_id = tag.identifier.hex().upper()
    tag_type = get_tag_info(tag)

    print(f"✅ Tag connected: [{tag_id}] - {tag_type}")

    # You can add logic here to read data from the tag if needed.
    # For now, we just identify it.

    # Returning False tells the connect loop to release the tag and look for a new one.
    return False

def main_loop(clf):
    """Main loop to continuously scan for tags."""
    print("\n--- Waiting for tag ---")
    
    # --- Key Change 2: Use rdwr options directly in the sense call ---
    # This allows the loop to correctly handle one tag at a time.
    rdwr_options = {
        'on-connect': on_connect,
        # 'on-release' can be added if you need to know when a tag is removed
        'terminate_on_timeout': True, # Exit if no tag is found in the timeout period
    }

    # --- Key Change 3: Define scan targets and override FeliCa command ---
    targets = [
        nfc.clf.RemoteTarget('106A'),
        nfc.clf.RemoteTarget('106B'),
        nfc.clf.RemoteTarget('212F', sensf_req=SENSF_REQ), # Override FeliCa polling here
        nfc.clf.RemoteTarget('424F', sensf_req=SENSF_REQ),
        # nfc.clf.RemoteTarget('15693')
    ]

    # The 'sense' method is better for a polling loop than 'connect'
    clf.sense(*targets, rdwr=rdwr_options, interval=0.1, timeout=2.0)

if __name__ == "__main__":
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("✅ RFID reader detected")
            print("-" * 30)
            print(f"  Device: {clf.device.vendor_name} {clf.device.product_name}")
            print(f"  Chipset: {clf.device._chipset_name}")
            print("-" * 30)
            
            while True:
                main_loop(clf)
                time.sleep(1) # Add a small delay between scans to reduce CPU usage

    except IOError:
        print("❌ Could not connect to RFID reader.")
        print("   Please check the driver installation and device connection.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")