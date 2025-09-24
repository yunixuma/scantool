import nfc
import binascii
import time

def process_tag(tag):
    """
    ISO/IEC 15693 タグを処理する関数
    """
    # タグが本当にType 5 (ISO/IEC 15693) か確認
    if not isinstance(tag, nfc.tag.tt5.Type5Tag):
        print(f"[!] This is not an ISO/IEC 15693 tag: {tag}")
        return

    print("\n" + "="*40)
    print("Found ISO/IEC 15693 (Type 5) Tag!")
    
    try:
        # UIDとシステム情報を表示
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

def main():
    """
    メイン処理
    """
    print("ISO/IEC 15693 Tag Reader")
    print("Waiting for a tag... Press Ctrl+C to exit.")

    # PaSoRiに接続
    with nfc.ContactlessFrontend('usb') as clf:
        while True:
            # ISO/IEC 15693ターゲットを探す
            target = nfc.clf.RemoteTarget("15693")
            # 0.5秒間隔でポーリング
            tag = clf.sense(target, interval=0.5)

            if tag:
                process_tag(tag)
                print("\n[*] Tag processing finished. Waiting for the next tag...")
                # 同じタグを連続で読み続けないように少し待つ
                time.sleep(3)
            else:
                continue

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Exiting program.")
    except Exception as e:
        print(f"[!] A critical error occurred: {e}")