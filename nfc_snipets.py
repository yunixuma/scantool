import sys
import nfc, nfc.clf
from nfc.clf import RemoteTarget
import binascii
import time
import my_common as my
import nfc_utils as nfcu

# デバッグ情報取得
import logging
logging.basicConfig(level=logging.DEBUG)

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
        my.perror("🔴 Unexpectedly disconnected from the tfag")


# NFCタグ接続時に呼び出されるコールバック関数
def on_connect(tag, clf):

    # tagの基本情報を表示
    print(tag)
    print(f"- Tag Type  : {tag.type}")
    print(f"- Maker     : {tag.manufacturer}")
    print(f"- IC Maker  : {tag.ic_manufacturer_name}")
    print(f"- Name      : {tag.name}")
    print(f"- Tag ID    : {binascii.hexlify(tag.identifier).upper()}")
    print(f"- Mem Size  : {tag.memory_size} bytes")
    print(f"- Block Size: {tag.block_size} bytes")
    print(f"- Blocks    : {tag.n_blocks} blocks")

    # is_dumpable属性でタグがダンプ可能か確認
    try:
        if not tag.is_dumpable:
            my.perror("This tag type cannot be dumped.")
            # FeliCa (Type 3 Tag) の場合は、サービスコードを指定して読む必要があることが多い
            if isinstance(tag, nfc.tag.tt3.Type3Tag):
                print("    This is a FeliCa tag. A generic dump may not be possible.")
                print("    You need to specify Service Codes to read data.")
            return True
    except nfc.tag.TagCommandError as e:
        my.perror(f"Dump failed: {e}")
        my.perror("    The tag may have read-protected areas.")
    except Exception as e:
        my.perror(f"An unexpected error occurred: {e}")
    try:
        memory_dump = tag.dump()

        print("[+] Memory Dump:")
        print("-" * 30)
        for line in memory_dump:
            print(line)
        print("-" * 30)
    except nfc.tag.TagCommandError as e:
        my.perror(f"Dump failed: {e}")
        my.perror("    The tag may have read-protected areas.")
    except Exception as e:
        my.perror(e)
    return True

    if isinstance(tag, nfc.tag.Type3Tag):
        print(f"- IDm        : {tag.idm .hex().upper()}")
        print(f"- System Code: {tag.system_code.hex().upper()}")
        print(f"- Service Code List: {[code.hex().upper() for code in tag.service_codes]}")
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
        return
    # if tag_type_str == "Type1Tag":
    if isinstance(tag, nfc.tag.Type1Tag):
        presence_check_target = nfc.clf.RemoteTarget(sdd_res=tag.sdd_res)
    # elif tag.type == 'Type2Tag':
    elif isinstance(tag, nfc.tag.Type2Tag):
        presence_check_target = nfc.clf.RemoteTarget(sdd_res=tag.sdd_res)
    # elif tag.type == 'Type3Tag':

    # elif tag.type == 'Type4ATag' or tag.type == 'Type4BTag':
    elif isinstance(tag, nfc.tag.Type4Tag):
        presence_check_target = nfc.clf.RemoteTarget(sel_res=tag.sel_res)
        try:
            uid_bytes = tag.identifier  # UID (IDm) をバイト列で取得
            uid_hex = binascii.hexlify(uid_bytes).decode('utf-8').upper()  # バイト列を16進数の文字列に変換して表示
            # print(f"Tag ID: {uid_hex}")
            print(f"Tag ID: {tag.identifier.hex().upper()}")  # タグのIDを表示

            initial_id = tag.identifier.hex().upper()
            print(f"Detected Type 4A Tag with initial (potentially random) ID: {initial_id}")

            # --- ▼▼▼ Final Diagnostic Test ▼▼▼ ---
            print("Attempting final diagnostic: ISO 7816-4 SELECT command...")
            try:
                # ISO/IEC 7816-4 SELECT by Name command
                # CLA=00, INS=A4, P1=04, P2=00, Lc=07, Data='1PAY.SYS.DDF01' (a common AID)
                select_command = bytearray.fromhex(my.AID['PAY_SYS_DDF01'])
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

    # タグがType 5 (ISO/IEC 15693) か確認
    elif isinstance(tag, nfc.tag.tt5.Type5Tag):
        print(f"This is an ISO/IEC 15693 (Type 5) tag: {tag}")
        return
    else:
        my.perror("Unknown tag type.")

    # n_blocks属性でブロック数を、block_size属性でブロックサイズを取得
    print(f"  - Memory Info: {tag.n_blocks} blocks, {tag.block_size} bytes/block")
    # 全てのブロックを読み出す
    print("[*] Reading all memory blocks...")
    # for block_num in range((tag.memory_size + 3) // 4):  # Type 2,4
    # for block_num in range((tag.memory_size + 7) // 8):  # TYpe 1
    for block_num in range(tag.n_blocks):
        try:
            # read_single_blockコマンドで1ブロックずつ読み込む
            block_data = tag.read_single_block(block_num)
            data_hex = binascii.hexlify(block_data).decode().upper()
            print(f"  - Block {block_num:02d}: {data_hex}")
        except nfc.tag.TagCommandError as e:
            # 読み取り禁止ブロックなどでエラーが発生した場合
            my.perror(f"  - Block {block_num:02d}: READ ERROR ({e})")
            continue # 次のブロックへ

    # Keep checking for the same tag as long as it's present and within the timeout
    while (time.time() - start_time) < SENSE_TIMEOUT:
        try:
            if clf.sense(presence_check_target) is None:
                print(f"✅ Tag released: [{tag_id}]")
                return True # Exit the function once the tag is removed

            time.sleep(0.1) # Wait a bit before checking again
        except Exception as e:
            my.perror(e)

def main_loop(clf):
    """Main loop to continuously scan for tags."""
    print("\n--- Waiting for tag ---")

    # --- Key Change 2: Use rdwr options directly in the sense call ---
    # This allows the loop to correctly handle one tag at a time.

    # --- Key Change 3: Define scan targets and override FeliCa command ---
    targets = TARGET_CODES

    # The 'sense' method is better for a polling loop than 'connect'
    target = clf.sense(*targets, rdwr=rdwr_options, interval=SENSE_INTERVAL, timeout=SENSE_TIMEOUT)
    if target:
        # Activate the tag to get a full Tag object
        tag = nfc.tag.activate(clf, target)
        on_connect(tag, clf)

if __name__ == '__main__':
    # USB接続のNFCリーダーを開く
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            rdwr_options = {
                # 'on-release' can be added if you need to know when a tag is removed
                'terminate_on_timeout': True, # Exit if no tag is found in the timeout period
                'targets': nfcu.TARGET_CODES,
                'on-startup': on_startup,
                'on-connect': lambda tag: on_connect(tag, clf),
                'on-release': on_release,
            }
            clf.connect(rdwr=rdwr_options, terminate_on_timeout=True, timeout=CONNECT_TIMEOUT)

            is_continue = True
            while True:
                main_loop(clf)
                nfcu.ask_continue()
                time.sleep(1) # Add a small delay between scans to reduce CPU usage

    except IOError:
        my.perror("Could not connect to the NFC reader.")
        my.perror("  Is the reader properly connected?", FALSE)
        my.perror("  On Linux/macOS, you may need to run with 'sudo'.", FALSE)
        sys.exit(1)
    except KeyboardInterrupt:
        my.perror("Interrupted by user.")
    finally:
        print("Script finished.")
    except Exception as e:
        my.perror(e)
