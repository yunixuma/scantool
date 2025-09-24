import os, sys
import nfc
# This line dynamically loads all available tag type modules (like Type1Tag, etc.)
# and makes them available for import.
# nfc.tag.discover()
from nfc.clf import RemoteTarget
# from nfc.tag import Type1Tag, Type2Tag, Type3Tag, Type4Tag, Type5Tag
import binascii
import datetime, time
import my_common as my

# TARGET_CODES = ['106A', '106B', '212F', '424F', '15693']
TARGET_CODES = ['106A', '106B', '212F', '424F', '212B'] # 212BはType4A
# --- 変更点 1: ポーリングするFeliCaのシステムコードを指定 ---
# ここでは「共通領域」を示す0xFE00を指定します。
# 交通系ICカードなど、特定のサービスを読みたい場合は、そのサービスのシステムコードに変更してください。
FELICA_SYSTEM_CODE = 0xFE00

def on_startup(targets):
    # print(f"targets: {targets}")
    print("The reader gets ready. Wait for detecting the tag...")
    # --- 変更点 2: FeliCaターゲットのポーリングコマンドを上書き ---
    for target in targets:
        print(f"target: {target.brty}")
        if isinstance(target, nfc.clf.RemoteTarget) and target.sensf_res:
            # sensf_reqはポーリングコマンドのバイト列です
            # [コマンドコード(0x00)][システムコード(2バイト)][リクエストコード(0x01)][タイムスロット(0x00)]
            target.sensf_req = bytearray()
    return targets

def on_release(tag):
    if tag:
        print(f"[{tag.identifier.hex().upper()}]: ✅ The tag has disconnected")
    else:
        print(my.S_ERROR + "🔴 Unexpectedly disconnected from the tfag")

def on_connect(tag, clf):
    print(f"Tag found: {tag}")
    tag_id = tag.identifier.hex().upper()
    print(f"✅ Tag connected: [{tag_id}]")
    
    # Determine the correct response attribute based on the tag type
    try:
        if isinstance(tag, nfc.tag.Type4Tag):
            presence_check_target = nfc.clf.RemoteTarget(sel_res=tag.sel_res)
        elif isinstance(tag, nfc.tag.Type2Tag):
            presence_check_target = nfc.clf.RemoteTarget(sdd_res=tag.sdd_res)
        else:
            # For other types, we can't reliably check for presence this way, so we just wait.
            print("   (Cannot perform presence check for this tag type, waiting 3s)")
            time.sleep(3)
            print(f"✅ Tag assumed released: [{tag_id}]")
            return True
        print("   Processing... (Waiting for tag to be removed, max 3 seconds)")
    except AttributeError:
        # print("   (Cannot perform presence check for this tag type, waiting 3s)")
        # time.sleep(3)
        print(f"🔴 Tag assumed released: [{tag_id}]")
        return True
    start_time = time.time()

    # Keep checking for the same tag as long as it's present and within the timeout
    while (time.time() - start_time) < 3.0:
        if clf.sense(presence_check_target) is None:
            print(f"✅ Tag released: [{tag_id}]")
            return True # Exit the function once the tag is removed
        
        time.sleep(0.1) # Wait a bit before checking again

    print(f"⚠️ Timeout reached. Tag [{tag_id}] was not removed in 3 seconds.")

    # if isinstance(tag, nfc.tag.tt3.Type3Tag):
    #     try:
    #         # システムコードを指定してポーリングした場合、IDmは安定して取得できることが多い
    #         idm = binascii.hexlify(tag.identifier).decode().upper()
    #         print("Found FeliCa (Type 3) Tag!")
    #         print(f"  - IDm: {idm}")
    #         print(f"  - System Code: {tag.system_code.hex().upper()}")
    #     except Exception as e:
    #         print(f"[!] Error: {e}")
    if isinstance(tag, nfc.tag.tt4.Type4ATag):
        try:
            initial_id = tag.identifier.hex().upper()
            print(f"Detected Type 4A Tag with initial (potentially random) ID: {initial_id}")

            # --- ▼▼▼ Final Diagnostic Test ▼▼▼ ---
            print("Attempting final diagnostic: ISO 7816-4 SELECT command...")
            try:
                # ISO/IEC 7816-4 SELECT by Name command
                # CLA=00, INS=A4, P1=04, P2=00, Lc=07, Data='1PAY.SYS.DDF01' (a common AID)
                select_command = bytearray.fromhex("00A4040007315041592E5359532E444446303100")
                
                response = tag.transceive(select_command)
                
                # If we get anything other than an error, it's a sign of life.
                print(f"✅ Diagnostic command sent. Response: {response.hex().upper()}")

            except nfc.tag.TagCommandError as e:
                # We expect an error here for this type of card.
                # The important part is the error code.
                print(f"🔴 Diagnostic command failed as expected. Error: {e}")
            # --- ▲▲▲ End of Final Test ▲▲▲ ---

        except Exception as e:
            print(f"[!] Error processing Type 4A tag: {e}")
    elif isinstance(tag, nfc.tag.tt1.Type1Tag):
        try:
            print("Found Topaz (Type 1) Tag!")
            uid_hex = binascii.hexlify(tag.identifier).decode().upper()
            print(f"  - UID: {uid_hex}")
            print(f"  - Manufacturer: {tag.manufacturer}")
            print(f"  - Memory Size: {tag.memory_size} bytes")
            print("="*40)

            # 全てのブロックを読み出す
            print("[*] Reading all memory blocks...")
            for block_num in range((tag.memory_size + 7) // 8):  # 1ブロックは8バイト
                try:
                    # read_blockコマンドで1ブロックずつ読み込む
                    block_data = tag.read_block(block_num)
                    data_hex = binascii.hexlify(block_data).decode().upper()
                    print(f"  - Block {block_num:02d}: {data_hex}")
                except nfc.tag.TagCommandError as e:
                    # 読み取り禁止ブロックなどでエラーが発生した場合
                    print(f"  - Block {block_num:02d}: READ ERROR ({e})")
                    continue # 次のブロックへ
        except Exception as e:
            print(f"[!] An unexpected error occurred: {e}") 
    elif isinstance(tag, nfc.tag.tt2.Type2Tag):
        try:
            print("Found MIFARE Ultralight (Type 2) Tag!")
            uid_hex = binascii.hexlify(tag.identifier).decode().upper()
            print(f"  - UID: {uid_hex}")
            print(f"  - Manufacturer: {tag.manufacturer}")
            print(f"  - Memory Size: {tag.memory_size} bytes")
            print("="*40)

            # 全てのブロックを読み出す
            print("[*] Reading all memory blocks...")
            for block_num in range((tag.memory_size + 3) // 4):  # 1ブロックは4バイト
                try:
                    # read_blockコマンドで1ブロックずつ読み込む
                    block_data = tag.read_block(block_num)
                    data_hex = binascii.hexlify(block_data).decode().upper()
                    print(f"  - Block {block_num:02d}: {data_hex}")
                except nfc.tag.TagCommandError as e:
                    # 読み取り禁止ブロックなどでエラーが発生した場合
                    print(f"  - Block {block_num:02d}: READ ERROR ({e})")
                    continue # 次のブロックへ
        except Exception as e:
            print(f"[!] An unexpected error occurred: {e}")
    elif isinstance(tag, nfc.tag.tt4.Type4BTag):
        try:
            print("Found Type 2 Tag (Type 4B)!")
            uid_hex = binascii.hexlify(tag.identifier).decode().upper()
            print(f"  - UID: {uid_hex}")
            print(f"  - Manufacturer: {tag.manufacturer}")
            print(f"  - Memory Size: {tag.memory_size} bytes")
            print("="*40)

            # 全てのブロックを読み出す
            print("[*] Reading all memory blocks...")
            for block_num in range((tag.memory_size + 3) // 4):  # 1ブロックは4バイト
                try:
                    # read_blockコマンドで1ブロックずつ読み込む
                    block_data = tag.read_block(block_num)
                    data_hex = binascii.hexlify(block_data).decode().upper()
                    print(f"  - Block {block_num:02d}: {data_hex}")
                except nfc.tag.TagCommandError as e:
                    # 読み取り禁止ブロックなどでエラーが発生した場合
                    print(f"  - Block {block_num:02d}: READ ERROR ({e})")
                    continue # 次のブロックへ
        except Exception as e:
            print(f"[!] An unexpected error occurred: {e}") 
    elif isinstance(tag, nfc.tag.tt5.Type5Tag):
        try:
            print("Found ISO/IEC 15693 (Type 5) Tag!")
            uid_hex = binascii.hexlify(tag.identifier).decode().upper()
            print(f"  - UID: {uid_hex}")
            print(f"  - Manufacturer: {tag.ic_manufacturer_name}")
            # n_blocks属性でブロック数を、block_size属性でブロックサイズを取得
            print(f"  - Memory Info: {tag.n_blocks} blocks, {tag.block_size} bytes/block")
            print("="*40)

            # 全てのブロックを読み出す
            print("[*] Reading all memory blocks...")
            for block_num in range(tag.n_blocks):
                try:
                    # read_single_blockコマンドで1ブロックずつ読み込む
                    block_data = tag.read_single_block(block_num)
                    data_hex = binascii.hexlify(block_data).decode().upper()
                    print(f"  - Block {block_num:02d}: {data_hex}")
                except nfc.tag.TagCommandError as e:
                    # 読み取り禁止ブロックなどでエラーが発生した場合
                    print(f"  - Block {block_num:02d}: READ ERROR ({e})")
                    continue # 次のブロックへ
        except Exception as e:
            print(f"[!] An unexpected error occurred: {e}")
    elif isinstance(tag, nfc.tag.tt3.Type3Tag):
        try:
            print(tag)
            print(tag.type)
            print(binascii.hexlify(tag.identifier).upper())
            print("Found FeliCa (Type 3) Tag!")
            uid_hex = binascii.hexlify(tag.identifier).decode().upper()
            print(f"  - UID: {uid_hex}")
            print(f"  - Manufacturer: {tag.manufacturer}")
            print(f"  - System Code: {tag.system_code.hex().upper()}")
            print(f"  - Service Code List: {[code.hex().upper() for code in tag.service_codes]}")
            print("="*40)

            # 全てのブロックを読み出す
            print("[*] Reading all memory blocks...")
            for service_code in tag.service_codes:
                try:
                    # read_without_encryptionコマンドで1ブロックずつ読み込む
                    block_data = tag.read_without_encryption([service_code], [0])
                    data_hex = binascii.hexlify(block_data[0]).decode().upper()
                    print(f"  - Service Code {service_code.hex().upper()}: {data_hex}")
                except nfc.tag.TagCommandError as e:
                    # 読み取り禁止ブロックなどでエラーが発生した場合
                    print(f"  - Service Code {service_code.hex().upper()}: READ ERROR ({e})")
                    continue # 次のサービスコードへ
        except Exception as e:
            print(my.S_ERROR + str(e))
    else:
        print(my.S_ERROR + "🔴 This tag type is not supported in this script.")
    # If return False, keep polling
    return True

def debug_device(dev):
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

def process_tag(tag):
    """Identifies a tag and prints its information."""
    
    # Use the tag's '.type' attribute for reliable identification
    tag_type_str = tag.type
    identifier = "N/A"
    
    print("-" * 30)

    if tag_type_str == "Type3Tag":
        # FeliCa (including Mobile Suica)
        identifier = tag.idm.hex().upper()
        print(f"✅ Detected: FeliCa (Type 3)")
        print(f"   IDm: {identifier}")
        print(f"   System Code: {tag.sys.hex().upper()}")

    elif tag_type_str == "Type4ATag" or tag_type_str == "Type4BTag":
        # ISO-DEP (ISO 14443-4) based cards
        identifier = tag.identifier.hex().upper()
        print(f"✅ Detected: {tag_type_str}")
        print(f"   UID: {identifier}")

        # Optional: Add logic here to get the real UID if it's a random UID card
        # This part is complex and specific to the card type (e.g., MIFARE DESFire)

    elif tag_type_str == "Type2Tag":
        # MIFARE Ultralight, NTAG, etc.
        identifier = tag.identifier.hex().upper()
        print(f"✅ Detected: {tag_type_str}")
        print(f"   UID: {identifier}")

    else:
        # Other tag types
        if tag.identifier:
            identifier = tag.identifier.hex().upper()
        print(f"✅ Detected: {tag_type_str}")
        print(f"   ID: {identifier}")

    print("-" * 30)

def touch_card(clf, is_continue):
    try:
        if is_continue is False:
            return False
        # target = clf.sense(RemoteTarget('106A'), RemoteTarget('106B'), RemoteTarget('212F'))
        # if target:
        #     print(f"  カードを検知: {target}")
        # else:
        #     print("  カードは見つかりませんでした。")
        print("Please touch the NFC card...")
        rdwr_options = {
            'targets': TARGET_CODES,
            'on-startup': on_startup,
            'on-connect': lambda tag: on_connect(tag, clf),
            'on-release': on_release,
        }    
        clf.connect(rdwr=rdwr_options, terminate_on_timeout=True, timeout=6)
        sensf_req_felica = bytearray.fromhex("00FE00010F") # Poll for System Code 0xFE00
        
        targets = [
            RemoteTarget('106A'),
            RemoteTarget('106B'),
            RemoteTarget('212F', sensf_req=sensf_req_felica),
            RemoteTarget('424F', sensf_req=sensf_req_felica),
        ]
        
        while True:
            print("\nPlease touch an NFC card... (Press Ctrl+C to exit)")
            
            # Scan for a tag for a limited time
            target = clf.sense(*targets, timeout=2.0)
            
            if target:
                # If a tag is found, activate it and process it
                tag = nfc.tag.activate(clf, target)
                process_tag(tag)
                
                # Wait for 3 seconds to avoid instantly re-reading the same card
                print("   (Waiting 3 seconds before next scan...)")
                time.sleep(3)

    except IOError:
        print("❌ Could not connect to RFID reader.")
    except KeyboardInterrupt:
        print("\n\n🛑 Script terminated by user.")
    except Exception as e:
        print(my.S_ERROR + str(e))
    return is_continue

def ask_continue():
    user_input = input("Scan another tag? (y/n): ").lower()
    if user_input in ['y', 'yes']:
        return True  # Continue the main while loop
    elif user_input in ['n', 'no']:
        return False # Break the main while loop
    else:
        print("Invalid input. Please enter 'y' or 'n'.")

def get_mobile_id(clf):
    """
    Polls for an iPhone's Suica and returns its IDm.
    """
    # 1. Create a specific polling command for FeliCa
    #    This command asks for any card with System Code 0xFE00 (common area)
    #    which is what Express Card mode often responds to.
    sensf_req_felica = bytearray.fromhex("00FE00010F")
    
    # 2. Define the target to search for
    felica_target = RemoteTarget('212F', sensf_req=sensf_req_felica)
    
    # 3. Use clf.sense() to look only for this specific target
    target = clf.sense(felica_target, timeout=0.5)
    
    if target:
        # Activate the tag to get a full Tag object
        tag = nfc.tag.activate(clf, target)
        
        # For Type3Tag (FeliCa), the ID is in the '.idm' attribute
        if isinstance(tag, nfc.tag.Type3Tag):
            return tag.idm.hex().upper()
            
    return None

def diagnose_tag(clf):
    """
    Scans for a tag and prints diagnostic information.
    """
    targets = [
        RemoteTarget('106A'), # For Type A based cards
        RemoteTarget('106B'), # For Type B based cards
        RemoteTarget('212F'), # For FeliCa
        RemoteTarget('424F'), # For FeliCa
        RemoteTarget('212B'), # For Type 4A cards
    ]

    print("\n--- Waiting for tag... ---")
    
    # 1. First, see what the reader physically senses
    target = clf.sense(*targets, timeout=1.0)

    if target is None:
        return # Nothing found, loop again

    # 2. Print the raw result from sense() for debugging
    print(f"DEBUG: sense() found a potential target: {target}")

    # 3. Try to activate it to get a full tag object
    try:
        tag = nfc.tag.activate(clf, target)
        print(f"DEBUG: activate() succeeded. Tag object: {tag}")
    except Exception as e:
        print(f"ERROR: Failed to activate tag. Reason: {e}")
        return

    # 4. Check the final type
    tag_type_str = tag.type
    identifier = tag.identifier.hex().upper() if tag.identifier else "N/A"
    
    print(f"  Result -> Type: {tag_type_str}, ID: {identifier}")
    print("-" * 30)

def get_tag_id(clf):
    # targets = [
    #     RemoteTarget('106A'),
    #     RemoteTarget('106B'),
    #     RemoteTarget('212B'),
    #     RemoteTarget('212F'),
    #     RemoteTarget('424F'),
    # ]
    # FeliCa (モバイルSuica含む) を探すための特別なターゲットを作成
    # System Code 0xFE00 (共通領域) を指定してポーリングするコマンド
    felica_target_212f = RemoteTarget("212F")
    felica_target_212f.sensf_req = bytearray.fromhex("00FE00010F")
    felica_target_424f = RemoteTarget("424F")
    felica_target_424f.sensf_req = bytearray.fromhex("00FE00010F")

    # 探したいターゲットのリストを定義
    targets = [
        RemoteTarget('106A'), # Type 2, Type 4A
        RemoteTarget('106B'), # Type 4B
        felica_target_212f,        # カスタマイズしたFeliCaターゲット
        felica_target_424f
    ]

    # 1. Find a potential target
    target = clf.sense(*targets, timeout=0.5)

    if target is None:
        return None, None

    # 2. Activate the tag. This loads the correct tag module and creates the object.
    tag = nfc.tag.activate(clf, target)
    
    # 3. Check the type of the activated object using its '.type' string attribute.
    tag_type_str = tag.type
    tag_type_display = "Unknown"
    identifier = None

    if tag_type_str == "Type3Tag":
        tag_type_display = "FeliCa (Type 3)"
        identifier = tag.idm.hex().upper() # FeliCa uses .idm
    elif tag_type_str in ["Type1Tag", "Type2Tag", "Type4ATag", "Type4BTag", "Type5Tag"]:
        identifier = tag.identifier.hex().upper() # Other types use .identifier
        if tag_type_str == "Type1Tag":
            tag_type_display = "Type 1"
        elif tag_type_str == "Type2Tag":
            tag_type_display = "Type 2"
        elif tag_type_str == "Type4ATag":
            tag_type_display = "Type 4A"
        elif tag_type_str == "Type4BTag":
            tag_type_display = "Type 4B"
        elif tag_type_str == "Type5Tag":
            tag_type_display = "Type 5"
    
    return tag_type_display, identifier

def wrapper(args):
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            debug_device(clf.device)
            is_continue = True
            while is_continue:
                get_mobile_id(clf)
                is_continue = touch_card(clf, is_continue)
                diagnose_tag(clf)
                tag_type, tag_id = get_tag_id(clf)
                if tag_id:
                    print(f"Detected {tag_type} tag with ID: {tag_id}")
                # is_continue = ask_continue()


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

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_dir = BASE_DIR + "/data/nfc"
    my.mkdir(data_dir, True)
    date = my.get_datetime()
    filepath = "nfc_" + date + ".csv"
    filepath = data_dir + "/" + filepath

    ret = wrapper(sys.argv)
    my.save_csv(ret, filepath)

    # finish_at = datetime.datetime.now()
    # print(f"Elapsed time: {finish_at - start_at}")
