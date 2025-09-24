import nfc
import sys
import logging

# nfcpyのデバッグ情報が不要な場合は以下の行をコメントアウト
# logging.basicConfig(level=logging.DEBUG)

def on_connect(tag):
    """
    NFCタグ接続時に呼び出されるコールバック関数
    """
    print(f"\n[*] Found Tag: {tag}")

    # is_dumpable属性でタグがダンプ可能か確認
    try:
        if not tag.is_dumpable:
            print("[!] This tag type cannot be dumped.")
            # FeliCa (Type 3 Tag) の場合は、サービスコードを指定して読む必要があることが多い
            if isinstance(tag, nfc.tag.tt3.Type3Tag):
                print("    This is a FeliCa tag. A generic dump may not be possible.")
                print("    You need to specify Service Codes to read data.")
            return True
    except nfc.tag.TagCommandError as e:
        print(f"[!] Dump failed: {e}")
        print("    The tag may have read-protected areas.")
    except Exception as e:
        print(f"[!] An unexpected error occurred: {e}")

    try:
        # tag.dump()メソッドでメモリ内容を読み出す
        # 各行が文字列としてリストで返される
        memory_dump = tag.dump()

        print("[+] Memory Dump:")
        print("-" * 30)
        for line in memory_dump:
            print(line)
        print("-" * 30)

    except nfc.tag.TagCommandError as e:
        print(f"[!] Dump failed: {e}")
        print("    The tag may have read-protected areas.")
    except Exception as e:
        print(f"[!] An unexpected error occurred: {e}")

    # Trueを返すと、1つのタグを処理した後にプログラムを終了する
    return True

def main():
    """
    メイン処理
    """
    print("NFC Tag Dumper")
    print("Waiting for a tag... Press Ctrl+C to exit.")
    
    try:
        # USB接続のNFCリーダーを開く
        with nfc.ContactlessFrontend('usb') as clf:
            # on_connectに関数を指定し、タグがタッチされるのを待つ
            clf.connect(rdwr={'on-connect': on_connect})

    except IOError:
        print("[!] Error: Could not connect to the NFC reader.", file=sys.stderr)
        print("    - Is the reader properly connected?", file=sys.stderr)
        print("    - On Linux/macOS, you may need to run with 'sudo'.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[*] Exiting.")
    finally:
        print("\nScript finished.")

if __name__ == '__main__':
    main()