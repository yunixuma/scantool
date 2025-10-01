import os, sys
import nfc
# This line dynamically loads all available tag type modules (like Type1Tag, etc.)
# and makes them available for import.
# nfc.tag.discover()
from nfc.clf import RemoteTarget
# from nfc.tag import Type1Tag, Type2Tag, Type3Tag, Type4Tag, Type5Tag
import binascii
import my_common as my

# Correctly build the FeliCa polling command ---
# [Command Code(0x00)][System Code(2 bytes, big-endian)][Request Code(0x01)][Time Slot(0x0F)]
SYSTEM_CODE = {
    'felica': 0xFE00,  # Suica, Edy, Nanaco, WAON, etc.
    'express': 0x0003, # iPhone Express Card mode
    'common':  0xFFFF, # Common area
}
AID = {
    'PAY_SYS_DDF01': "00A4040007315041592E5359532E444446303100"
}
SENSF_REQ_FELICA = bytearray([0x00]) + SYSTEM_CODE['felica'].to_bytes(2, 'big') + bytearray([0x01, 0x0F])
# SENSF_REQ_FELICA = bytearray.fromhex("00FE00010F")
SENSF_REQ_EXPRESS = bytearray.fromhex("000003010F")
TARGET_CODES = {
    'express': [
        RemoteTarget('212F', sensf_req=SENSF_REQ_EXPRESS),  # Override iPhone Express Mode polling here
        RemoteTarget('424F', sensf_req=SENSF_REQ_EXPRESS),
    ],
    'felica': [
        RemoteTarget('212F', sensf_req=SENSF_REQ_FELICA),  # Override FeliCa polling here
        RemoteTarget('424F', sensf_req=SENSF_REQ_FELICA),
    ],
    'mifare': [
        RemoteTarget('106A'),
        RemoteTarget('106B'),
        RemoteTarget('212A'),
        RemoteTarget('212B')
    ],
    'felica-lite': [
        RemoteTarget('212F'),
        RemoteTarget('424F'),
    ],
    'other': [
        RemoteTarget('424A'),
        RemoteTarget('424B'),
        RemoteTarget('848A'),
        RemoteTarget('848B'),
        RemoteTarget('848F'),        
        # RemoteTarget('15693')
    ]
}
CONNECT_TIMEOUT = 10
SENSE_INTERVAL = 0.1
SENSE_TIMEOUT = 0.5

def get_mobile_suica_idm(clf):
    # 1. Create a specific polling command for Suica (System Code 0x0003)
    felica_target = RemoteTarget('212F', sensf_req=SENSF_REQ_FELICA)

    # 2. Use clf.sense() to look only for this specific target
    target = clf.sense(felica_target, timeout=0.5)

    if target is None:
        return None

    try:
        # 3. Activate the tag. This is a crucial step.
        #    It identifies the tag and loads the correct module internally.
        tag = nfc.tag.activate(clf, target, timeout=SENSE_TIMEOUT)

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

def get_tag_type(tag):
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

def ask_continue():
    user_input = input("Scan another tag? (y/n): ").lower()
    if user_input in ['y', 'yes']:
        return True  # Continue the main while loop
    elif user_input in ['n', 'no']:
        return False # Break the main while loop
    else:
        print("Invalid input. Please enter 'y' or 'n'.")

def debug_reader(dev):
    print("✅ RFID reader detected")
    print("-" * 30)
    # print(dir(dev))
    # print(f"  Vendor : {dev._vendor_name}")
    print(f"  Vendor : {dev.vendor_name}")
    print(f"  Product: {dev.product_name}")
    print(f"  Chipset: {dev._chipset_name}")
    print(f"  Path   : {dev.path}")
    # print(f"  Encode : {dir(dev._chipset_name.encode)}")
    # print(f"  Format : {dir(dev._chipset_name.format)}")
    # for key, value in dev.chipset.__dict__.items():
    #     print(f"    {key}: {value}")
    #     for sub_key, sub_value in value.__dict__.items():
    #         print(f"      {sub_key}: {sub_value}")
    # print("-" * 30)
    # print(vars(dev))
    print("-" * 40)
    sys.stdout.flush()
