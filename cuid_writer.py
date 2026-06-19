import os
import sys
import csv
import argparse
import yaml
from smartcard.System import readers
from colorama import init, Fore, Style

init(autoreset=True)

def getch():
    if sys.platform == 'win32':
        import msvcrt
        ch = msvcrt.getch()
        try:
            return ch.decode('utf-8').upper()
        except UnicodeDecodeError:
            return ''
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if ch == '\x03':
            return 'C'
        return ch.upper()

def connect_reader():
    r = readers()
    if not r:
        raise Exception("NFCリーダーが検出されません。")
    connection = r[0].createConnection()
    connection.connect()
    return connection

def execute_apdu(conn, apdu, error_msg):
    response, sw1, sw2 = conn.transmit(apdu)
    if sw1 != 0x90 or sw2 != 0x00:
        raise Exception(f"{error_msg} (SW1={hex(sw1)}, SW2={hex(sw2)})")
    return response

def load_key(conn, key_bytes):
    apdu = [0xFF, 0x82, 0x00, 0x00, 0x06] + key_bytes
    execute_apdu(conn, apdu, "鍵のロードに失敗しました")

def authenticate(conn, block_num, key_type=0x60):
    apdu = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_num, key_type, 0x00]
    execute_apdu(conn, apdu, f"ブロック {block_num} のセクタ認証に失敗しました")

def read_block(conn, block_num):
    apdu = [0xFF, 0xB0, 0x00, block_num, 0x10]
    return execute_apdu(conn, apdu, f"ブロック {block_num} の読み取りに失敗しました")

def write_block(conn, block_num, data):
    if len(data) != 16:
        raise Exception("書き込みデータ長は正確に16バイトである必要があります。")
    apdu = [0xFF, 0xD6, 0x00, block_num, 0x10] + data
    execute_apdu(conn, apdu, f"ブロック {block_num} の書き込みに失敗しました")

def authenticate_for_write(conn, target_block, auth_key_b_list):
    default_key = [0xFF] * 6
    try:
        load_key(conn, default_key)
        authenticate(conn, target_block, key_type=0x60)
        return
    except Exception:
        pass

    try:
        load_key(conn, auth_key_b_list)
        authenticate(conn, target_block, key_type=0x61)
        return
    except Exception:
        raise Exception(f"セクタ認証拒否 (ブロック{target_block}): 初期鍵およびセットアップ用鍵(Key B)のいずれも一致しません。")

def parse_and_pad_data(val_str, is_uid=False):
    """
    入力文字列をラテラルの記述規則に従って型推論し、
    MIFARE Classicのブロック構造に合致するようパディングしたバイト列を生成します。
    """
    if not val_str:
        return None
    val_str = val_str.strip()
    
    max_len = 4 if is_uid else 16

    # 1. クォーテーションで囲まれている場合（文字列ラテラル）
    if (val_str.startswith('"') and val_str.endswith('"')) or \
       (val_str.startswith("'") and val_str.endswith("'")):
        content = val_str[1:-1]
        b_data = content.encode('utf-8')
        if len(b_data) > max_len:
            raise Exception(f"文字列データ'{content}'が最大サイズ({max_len}バイト)を超過しています。")
        # 文字列の場合はそのまま左詰め配置し、余白をNullバイトで埋める
        b_data += b'\x00' * (max_len - len(b_data))
        return list(b_data)
        
    # 2. 数値ラテラル判定とパース
    try:
        num = None
        # UID特例対応: 0xプレフィックスなしの8文字HEX文字列へのフォールバック
        if is_uid and len(val_str) == 8 and all(c in '0123456789abcdefABCDEF' for c in val_str):
            num = int(val_str, 16)
        elif val_str.lower().startswith('0x'):
            num = int(val_str, 16)
        elif val_str.lower().startswith('0b'):
            num = int(val_str, 2)
        elif val_str.lstrip('-').isdigit():
            num = int(val_str, 10)
            
        # いずれの数値リテラルにも合致しない場合は、暗黙的に文字列としてフォールバック処理
        if num is None:
            b_data = val_str.encode('utf-8')
            if len(b_data) > max_len:
                raise Exception(f"文字列データ'{val_str}'が最大サイズ({max_len}バイト)を超過しています。")
            b_data += b'\x00' * (max_len - len(b_data))
            return list(b_data)

        # 3. 数値データのパディング処理
        # ブロック先頭から4byte長のコンテナ単位で配置し、余白はNullバイトで埋める
        if num == 0:
            byte_len = 1
        else:
            # 負の数(2の補数表現)を考慮した必要バイト数の算出
            byte_len = (num.bit_length() + (1 if num < 0 else 0) + 7) // 8
            
        # 4バイトの倍数境界に切り上げ (最小4バイト)
        padded_len = max(4, ((byte_len + 3) // 4) * 4)
        
        if padded_len > max_len:
            raise Exception(f"数値データが最大サイズ({max_len}バイト)を超過しています。")
            
        # ビッグエンディアン配列への変換
        b_data = num.to_bytes(padded_len, byteorder='big', signed=(num < 0))
        # 16バイト(UIDは4バイト)に満たない末尾の余白をNullバイトで埋める
        b_data += b'\x00' * (max_len - padded_len)
        return list(b_data)
        
    except ValueError as e:
        raise Exception(f"データ '{val_str}' のパースに失敗しました: {e}")

def draw_progressbar(prefix, current, total, bar_length=30, color=Fore.CYAN):
    """
    標準出力にテキストベースのプログレスバーを描画します。
    キャリッジリターン(\r)を用いて同一行を上書き更新します。
    """
    percent = float(current) * 100 / total if total > 0 else 100.0
    filled_length = int(bar_length * current // total) if total > 0 else bar_length
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r{color}{prefix} |{bar}| {percent:.1f}% ({current}/{total}){Style.RESET_ALL}')
    sys.stdout.flush()

def process_tag(row, target_sector, auth_key_a_list, auth_key_b_list, lock_other_sectors, progress_callback=None):
    name = row.get('name', '').strip()
    uid_str = row.get('uid', '').strip()

    # 各データブロックのペイロードパースとパディング
    d0 = parse_and_pad_data(row.get('data0', '').strip())
    d1 = parse_and_pad_data(row.get('data1', '').strip())
    d2 = parse_and_pad_data(row.get('data2', '').strip())

    conn = connect_reader()
    base_block = target_sector * 4
    trailer_block = base_block + 3

    # 対象セクタへの認証を実行
    authenticate_for_write(conn, base_block, auth_key_b_list)

    # データの個別書き込み（CSVに値が存在するもののみ実行）
    if d0 is not None:
        write_block(conn, base_block + 0, d0)
    if d1 is not None:
        write_block(conn, base_block + 1, d1)
    if d2 is not None:
        write_block(conn, base_block + 2, d2)

    # セクタトレイラーの書き込み（Key A: 読み取り専用 / Key B: 読み書き用）
    new_trailer = auth_key_a_list + [0x78, 0x77, 0x88, 0x69] + auth_key_b_list
    write_block(conn, trailer_block, new_trailer)
    
    processed_sectors = 1
    if progress_callback:
        progress_callback(processed_sectors)

    # CUID (Block 0) のUID書き換えおよび保護処理
    if uid_str:
        uid_list = parse_and_pad_data(uid_str, is_uid=True)
        # Block 0 Byte 4のBCC(UIDのXOR)を算出
        bcc = uid_list[0] ^ uid_list[1] ^ uid_list[2] ^ uid_list[3]

        # セクタ0の認証
        authenticate_for_write(conn, 0, auth_key_b_list)

        # Block 0を読み出し、メタデータ(SAK/ATQA/Manufacturer)を保持して書き戻す
        block0_data = read_block(conn, 0)
        new_block0 = uid_list + [bcc] + block0_data[5:16]
        write_block(conn, 0, new_block0)

        # セクタ0のトレイラー(ブロック3)に同じ権限を適用してロック
        write_block(conn, 3, new_trailer)
        
        processed_sectors += 1
        if progress_callback:
            progress_callback(processed_sectors)

    # YAMLで指定された他のセクタを同一のKeyでロックする処理
    for sec in lock_other_sectors:
        # メイン処理で既にロック済みのセクタはスキップ
        if sec == target_sector:
            continue
        if sec == 0 and uid_str:
            continue
            
        if sec < 0 or sec > 15:
            continue
            
        sec_base = sec * 4
        sec_trailer = sec_base + 3
        
        try:
            authenticate_for_write(conn, sec_base, auth_key_b_list)
            write_block(conn, sec_trailer, new_trailer)
            
            processed_sectors += 1
            if progress_callback:
                progress_callback(processed_sectors)
        except Exception as e:
            raise Exception(f"セクタ {sec} のロック処理中にエラーが発生しました: {e}")

def main():
    parser = argparse.ArgumentParser(description="CUID Writer - YAML Config & Literal Parsing")
    parser.add_argument("csv_file", help="読み込むCSVファイルのパス")
    parser.add_argument("yaml_file", help="読み込むYAML設定ファイルのパス")
    args = parser.parse_args()

    if not os.path.exists(args.yaml_file) or not os.path.exists(args.csv_file):
        print(f"{Fore.RED}エラー: 指定されたファイルが存在しません。")
        sys.exit(1)

    try:
        with open(args.yaml_file, 'r', encoding='utf-8') as yf:
            config = yaml.safe_load(yf) or {}

        target_sector_val = config.get('target_sector')
        if target_sector_val is None:
            raise ValueError("target_sectorが定義されていません。")
        target_sector = int(target_sector_val)
        if target_sector < 0 or target_sector > 15:
            raise ValueError("target_sectorは0〜15の範囲で指定して下さい。")

        auth_key_a_hex = config.get('auth_key_a')
        auth_key_b_hex = config.get('auth_key_b')
        if not auth_key_a_hex or not auth_key_b_hex:
            raise ValueError("auth_key_aまたはauth_key_bが定義されていません。")
        
        auth_key_a_list = list(bytes.fromhex(auth_key_a_hex))
        auth_key_b_list = list(bytes.fromhex(auth_key_b_hex))

        # 他のセクタをロックする設定のパース
        lock_val = config.get('lock_other_sectors', [])
        if str(lock_val).lower() == 'all':
            lock_other_sectors = list(range(16))
        elif isinstance(lock_val, list):
            lock_other_sectors = [int(s) for s in lock_val]
        else:
            raise ValueError("lock_other_sectorsはリスト形式、または 'all' を指定して下さい。")

    except Exception as e:
        print(f"{Fore.RED}YAML設定ファイルの読み込みエラー: {e}")
        sys.exit(1)

    with open(args.csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        records = list(reader)
        total_records = len(records)
        
        if total_records == 0:
            print(f"{Fore.YELLOW}CSVファイルに処理対象のレコードがありません。")
            sys.exit(0)

        for record_index, row in enumerate(records):
            name = row.get('name', 'N/A')
            uid_str = row.get('uid', '').strip()
            
            # このレコードで処理する予定の全セクタ数を計算
            total_sectors_to_process = 1 # target_sector
            if uid_str:
                total_sectors_to_process += 1 # sector 0
            
            valid_locks = [s for s in lock_other_sectors if s != target_sector and not (s == 0 and uid_str) and 0 <= s <= 15]
            total_sectors_to_process += len(valid_locks)
            
            while True:
                print(f"\n{'-'*50}")
                draw_progressbar("全体進捗", record_index, total_records, color=Fore.YELLOW)
                print(f"\n[{name}] の書き込み準備完了")
                print("RFIDタグをかざし、[Space]または[Enter]を押して下さい。([C]または[A]で終了)")
                
                while True:
                    key = getch()
                    if key in (' ', '\r', '\n'):
                        break
                    elif key in ('C', 'A'):
                        print("処理を中断します。")
                        sys.exit(0)

                try:
                    # セクタ進捗を更新するコールバック関数
                    def cb_sector_progress(current_sector):
                        draw_progressbar("セクタ処理", current_sector, total_sectors_to_process, color=Fore.CYAN)
                        
                    process_tag(row, target_sector, auth_key_a_list, auth_key_b_list, lock_other_sectors, progress_callback=cb_sector_progress)
                    print(f"\n{Fore.GREEN}書き込み成功: {name}{Style.RESET_ALL}")
                    break
                except Exception as e:
                    print(f"\n{Fore.RED}エラー: {e}{Style.RESET_ALL}")
                    print("再試行するには [R] を、スキップするには [N] を押して下さい。([C]/[A]で終了)")
                    
                    retry_or_skip = False
                    while True:
                        key2 = getch()
                        if key2 == 'R':
                            break
                        elif key2 == 'N':
                            retry_or_skip = True
                            break
                        elif key2 in ('C', 'A'):
                            print("処理を中断します。")
                            sys.exit(0)
                    
                    if retry_or_skip:
                        print(f"{name} の処理をスキップしました。")
                        break

    print(f"\n{'-'*50}")
    draw_progressbar("全体進捗", total_records, total_records, color=Fore.YELLOW)
    print("\n全てのレコードの処理が完了しました。")

if __name__ == '__main__':
    main()