import http.server
import ssl
import socketserver

# --- 設定 ---
HOST = '0.0.0.0'  # すべてのインターフェースで待機
PORT = 8443       # HTTPS用のポート番号

# HTTPリクエストを処理するハンドラ
handler = http.server.SimpleHTTPRequestHandler

# TCPサーバーを作成し、SSL/TLSでラップする
with socketserver.TCPServer((HOST, PORT), handler) as httpd:
    print(f"HTTPSサーバーを起動します: https://{HOST}:{PORT}")

    # SSLコンテキストを作成し、証明書ファイルを指定
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(keyfile="key.pem", certfile="cert.pem")

    # サーバーソケットをSSLでラップ
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

    # サーバーを永久に実行
    httpd.serve_forever()
