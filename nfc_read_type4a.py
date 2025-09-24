# uid_reader.py
import nfc
import binascii

def on_connect(tag):
    """
    NFCタグが接続されたときに呼び出される関数
    """
    print(f"[*] Tag found: {tag}")

    # タグがType 4Aであることを確認
    if isinstance(tag, nfc.tag.tt4.Type4ATag):
        try:
            # print(tag.name)  # タグの名前を表示
            print(f" [+] Tag Type: {tag.type}")
            print(f" [+] Tag ID: {tag.identifier.hex().upper()}")  # タグのIDを表示
            # UID (IDm) をバイト列で取得
            uid_bytes = tag.identifier
            # バイト列を16進数の文字列に変換して表示
            uid_hex = binascii.hexlify(uid_bytes).decode('utf-8').upper()
            print(f" [+] UID (IDm): {uid_hex}")
        except Exception as e:
            print(f"[!] Error: {e}")
    else:
        print("[!] Not a Type4A Tag.")
    
    # Falseを返すとポーリングを続ける
    return False

def main():
    """
    メイン処理
    """
    # PaSoRi (USB接続のリーダー) を開く
    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("PaSoRi (RC-S380) is ready.")
            print("Please touch your NFC tag...")
            # リモートターゲット（NFCタグ）に接続するまで待機
            # on_connectに関数を指定し、タグ検出時に呼び出す
            clf.connect(rdwr={'on-connect': on_connect})
    except IOError:
        print("[!] Could not connect to PaSoRi.")
        print("[!] Please check the driver installation and device connection.")
    except Exception as e:
        print(f"[!] An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
    