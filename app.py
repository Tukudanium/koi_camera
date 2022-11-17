import os
from base64 import b64encode, b64decode
import cv2
from werkzeug.utils import secure_filename
from flask import *
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)

image = '' #差し替え後の画像の保存位置
stop_run = False #カメラのオンオフ
stopped = True #動画停止用フラグ


#################
## ページ
#################

#動画を表示するURL
@app.route('/',methods=['POST','GET'])
def main_page():
    if request.method == 'GET':
        global stop_run
        stop_run = True #カメラを止める
        while stopped == False:
            stopped #カメラの処理が終了するまで待つ

        return render_template("index.html")
    if request.method == 'POST':
        return

#ボタンを押したタイミングの画像を取得するURL
@app.route('/save')
def save_page():
    global stop_run
    stop_run = True #カメラを止める
    return render_template("result.html")

#動画のURL
#撮影画面のimgにこのURLをsrcに設定することでストリーミング再生を実装している
@app.route('/video')
def video_feed():
    global stop_run
    stop_run = False #カメラを動かす
    # コマ撮りの画像を常に更新し続ける
    return Response(getFrames(), mimetype='multipart/x-mixed-replace; boundary=boundary')


#################
## API
#################

#画像取得API jsで呼び出す
#処理済みのキャプチャ画像をbase64に変換して返す
@app.route('/image',methods=['GET'])
def image_api():
    if request.method == 'GET':
        global image
        text = str(b64encode(image), "utf-8")
        message = {'image': text}
        return jsonify(message)

#顔差し替え画像変更API jsで呼び出す
#顔に重ねる画像を、URLで指定された名前のPNG画像に変更する
@app.route('/koiChange/<image_name>',methods=['GET'])
def koichange_api(image_name):
    if request.method == 'GET':
        global img_file_path
        img_file_path = os.path.join(img_module_dir, image_name + '.png')
        return ("nothing")


#################
## 画像処理
#################

# 重ねる画像
img_module_dir = os.path.dirname(__file__) + '\image'
img_file_path = os.path.join(img_module_dir, 'tai.png')
# https://github.com/opencv/opencv/tree/master/data/haarcascades
# 顔認識用学習済みデータ　カスケード分類器
module_dir = os.path.dirname(__file__)
file_path = os.path.join(module_dir, 'haarcascade_frontalface_default.xml')
cascade = cv2.CascadeClassifier(file_path)

#端末のカメラから画像を取得し続け、顔を認識したら画像を重ねて配置する関数
#フレームごとの画像を返し続ける
def getFrames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # カメラが複数あるときは 0を1や2にする
    global stop_run
    global stopped
    stopped = False
    aveSize = 0
    count = 0
    while cap.isOpened():
        if stop_run:
            #カメラ停止フラグがあったら処理を中断
            cap.release()
            break
        else:
            try:
                faceImg = cv2.imread(img_file_path, cv2.IMREAD_UNCHANGED) #画像
                _, frame = cap.read()
                image_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                facerect = cascade.detectMultiScale(
                    image_gray, scaleFactor=1.1, minNeighbors=2, minSize=(30, 30)) #顔の範囲を取得
                # 顔を検出した場合
                if len(facerect) > 0:
                    for rect in facerect:
                        count += 1
                        if count < 4:
                            aveSize += (rect[2] + rect[3]) / 2
                            break
                        elif count == 4:
                            aveSize += (rect[2] + rect[3]) / 2
                            aveSize /= 5
                        else:
                            aveSize = aveSize * 0.8 + rect[2] * 0.1 + rect[3] * 0.1
                        thresh = aveSize * 0.95  # 移動平均の95%以上を閾値
                        if rect[2] < thresh or rect[3] < thresh:
                            break
                        # 検出した顔を囲む矩形の作成
                        #color = (255, 100, 100)
                        #cv2.rectangle(frame, tuple(rect[0:2]), tuple( rect[0:2]+rect[2:4]), color, thickness=2)
                        faceImg = cv2.resize(
                            faceImg, ((int)(rect[2] * 1.3), (int)(rect[3] * 1.3)), cv2.IMREAD_UNCHANGED)
                        rect[0] -= rect[2] * 0.15  # x_offset
                        rect[1] -= rect[3] * 0.15  # y_offset
                        # 顔の部分に画像挿入
                        #FIXME 顔を大きく近づけたり、画面端に顔があるとエラー
                        #      おそらく表示している画面の範囲を顔の認識部分が超えてしまったことによる
                        #      強制終了する訳では無いが、エラー中は重ねる画像は出ない
                        frame[rect[1]:rect[1] + faceImg.shape[0],rect[0]:rect[0] + faceImg.shape[1]] = frame[rect[1]:rect[1] + faceImg.shape[0], rect[0]:rect[0] + faceImg.shape[1]] * (1 - faceImg[:, :, 3:] / 255) + faceImg[:, :, :3] * (faceImg[:, :, 3:] / 255)
                global image #現在の画像を更新
                ret, image = cv2.imencode(".jpg", frame)
                #画像表示
                yield (b'--boundary\r\nContent-Type: image/jpeg\r\n\r\n' + image.tostring() + b'\r\n\r\n')
            except:
                print ('=== getFrames() エラー内容 ===')
                import traceback
                traceback.print_exc() #エラー表示
                print ('=============================')
                pass
    #カメラ終了時に停止フラグを立てて修了
    cv2.destroyAllWindows()
    cap.release()
    stopped = True
    return

#ブラウザでローカルホストを自動で開くだけ
import webbrowser
webbrowser.get().open("http://localhost:5000/")
