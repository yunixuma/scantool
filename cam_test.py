import cv2
from cv2_enumerate_cameras import enumerate_cameras

# 利用可能なカメラを列挙し、ユーザーに選択させる
camera_devices = list(enumerate_cameras(cv2.CAP_DSHOW))
if not camera_devices:
    print("エラー: 利用可能なカメラが見つかりません。")
    exit()

print("利用可能なカメラ:")
for i, cam in enumerate(camera_devices):
    print(f"  {i}: {cam.name} (インデックス: {cam.index})")

try:
    choice = int(input("使用するカメラの番号を選択してください: "))
    if not 0 <= choice < len(camera_devices):
        raise ValueError
    selected_camera = camera_devices[choice]
    camera_index = selected_camera.index
except (ValueError, IndexError):
    print("無効な選択です。プログラムを終了します。")
    exit()

# 選択されたカメラをCAP_DSHOWバックエンドで開く
cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

# カメラが正常に開かれたか確認
if not cap.isOpened():
    print(f"エラー: カメラ {camera_index} を開けませんでした。")
    print("Windowsのカメラパーミッション、他のアプリによる使用、ドライバの問題を確認してください。")
    exit()

print(f"カメラ '{selected_camera.name}' を開きました。'q'キーを押して終了します。")

while True:
    # フレームをキャプチャ
    ret, frame = cap.read()

    # フレームが正しく読み取れたか確認
    if not ret:
        print("エラー: フレームをキャプチャできませんでした。")
        break

    # フレームを表示
    cv2.imshow('Camera Feed', frame)

    # 'q'キーが押されたらループを抜ける
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 後処理
cap.release()
cv2.destroyAllWindows()
print("カメラを解放し、ウィンドウを閉じました。")