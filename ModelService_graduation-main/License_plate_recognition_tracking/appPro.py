import eventlet
eventlet.monkey_patch()
from flask import Flask, request, jsonify, render_template, send_from_directory, Response, send_file
import os
import cv2
import json
import gzip
import base64
import time
from flask_cors import CORS
import torch
import numpy as np
from ultralytics import YOLO
from utilss.timers import FPSBasedTimer
from utilss.generaltime import find_in_list, load_zones_config
import supervision as sv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from flask import Flask, render_template, Response, request, redirect, url_for
import cv2
from scripts.Car_recognition import detect_Recognition_plate, load_model, draw_result
from car_recognition.car_rec import init_car_rec_model,get_color_and_score
from plate_recognition.plate_rec import get_plate_result,allFilePath,init_model,cv_imread
import os
import numpy as np
import uuid
from models.check_login import is_existed,exist_user,is_null
from models.regist_login import add_user
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, current_user
import torch
from flask_socketio import SocketIO, emit
from flask_socketio import emit
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory

from flask_cors import CORS
from flask_socketio import emit
import base64
import threading
from queue import Queue
from flask import send_from_directory
import logging
import eventlet
import templates.config as config
from flask import Flask, request, jsonify, render_template
import smtplib
from email.mime.text import MIMEText
import uuid
from datetime import datetime, timedelta
from flask import url_for
from flask import Flask, request, jsonify, render_template
import smtplib
from email.mime.text import MIMEText
import uuid
from datetime import datetime, timedelta
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask import request, redirect, url_for
from werkzeug.utils import secure_filename

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# eventlet.monkey_patch()

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 设置最大文件上传大小为 1GB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 导入车牌识别工作流模块
try:
    from plate_workflow import plate_workflow
    # 注册车牌识别工作流蓝图
    app.register_blueprint(plate_workflow, url_prefix='/plate_workflow')
    print("已成功加载车牌识别工作流模块")
except Exception as e:
    print(f"加载车牌识别工作流模块失败: {str(e)}")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')



COLORS = sv.ColorPalette.from_hex(["#E6194B", "#3CB44B", "#FFE119", "#3C76D1"])
COLOR_ANNOTATOR = sv.ColorAnnotator(color=COLORS)
LABEL_ANNOTATOR = sv.LabelAnnotator(
    color=COLORS, text_color=sv.Color.from_hex("#000000")
)


def send_email(sender_email, app_password, receiver_email, subject, body):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    try:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"Error occurred while sending email: {str(e)}")
    finally:
        server.quit()

def traffic_video(video_file, json_file, json_path, model_weights, device, confidence_threshold, iou_threshold, classes_to_track, receiver_email):
    # 读取视频文件

    detected_overtime = False  # 标志变量,表示是否检测到超时
    video_capture = cv2.VideoCapture(video_file)

    # 加载JSON文件
    if json_file:
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], json_file.filename)
        json_file.save(json_path)
    elif json_path:
        json_path = json_path
    else:
        return None  # 如果没有提供JSON文件或路径,返回None

    # 加载模型
    model = YOLO(model_weights)

    # 初始化跟踪器
    tracker = sv.ByteTrack(minimum_matching_threshold=0.5)

    # 获取视频信息
    if video_file:
        video_info = sv.VideoInfo.from_video_path(video_path=video_file)
    else:
        video_info = sv.VideoInfo(fps=30)  # 使用默认 FPS 值

    # 获取视频分辨率
    _, frame = video_capture.read()
    resolution_wh = frame.shape[1], frame.shape[0]

    # 加载区域配置
    polygons = load_zones_config(file_path=json_path)
    zones = [
        sv.PolygonZone(
            polygon=polygon,
            frame_resolution_wh=resolution_wh,
            triggering_anchors=(sv.Position.CENTER,),
        )
        for polygon in polygons
    ]
    timers = [FPSBasedTimer(video_info.fps) for _ in zones]

    # 创建视频编码器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('static/processed_video.mp4', fourcc, video_info.fps, (frame.shape[1], frame.shape[0]))

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        device_str = device
        if device_str == "cuda" and not torch.cuda.is_available():
            print("CUDA 设备不可用,使用 CPU")
            device_str = "cpu"

        results = model(frame, verbose=False, device=device_str, conf=confidence_threshold)[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = detections[find_in_list(detections.class_id, classes_to_track)]
        detections = detections.with_nms(threshold=iou_threshold)
        detections = tracker.update_with_detections(detections)

        annotated_frame = frame.copy()

        for idx, zone in enumerate(zones):
            annotated_frame = sv.draw_polygon(
                scene=annotated_frame, polygon=zone.polygon, color=COLORS.by_idx(idx)
            )

            detections_in_zone = detections[zone.trigger(detections)]
            time_in_zone = timers[idx].tick(detections_in_zone)
            custom_color_lookup = np.full(detections_in_zone.class_id.shape, idx)

            annotated_frame = COLOR_ANNOTATOR.annotate(
                scene=annotated_frame,
                detections=detections_in_zone,
                custom_color_lookup=custom_color_lookup,
            )
            labels = [
                f"#{tracker_id} {int(time // 60):02d}:{int(time % 60):02d}"
                for tracker_id, time in zip(detections_in_zone.tracker_id, time_in_zone)
            ]
            annotated_frame = LABEL_ANNOTATOR.annotate(
                scene=annotated_frame,
                detections=detections_in_zone,
                labels=labels,
                custom_color_lookup=custom_color_lookup,
            )

            # 检查是否有车辆在指定区域内超过一秒
            if any(time >= 1 for time in time_in_zone):
                detected_overtime = True  # 设置标志变量为 True

        # 将帧添加到视频编码器
        out.write(annotated_frame)

    video_capture.release()
    out.release()

    # 如果检测到超时,发送邮件通知
    if detected_overtime:
        sender_email = "1241515924@qq.com"
        app_password = "lszowfvdnwwxjged"
        # receiver_email = "1610038995@qq.com"
        subject = "Vehicle Detected"
        body = "A vehicle has been detected in the specified zone for more than 1 second."
        send_email(sender_email, app_password, receiver_email, subject, body)

    return 'static/processed_video.mp4'

@app.route('/')
def index():
    app.logger.info('Info level log')
    app.logger.warning('Warning level log')
    return redirect(url_for('user_login'))

@app.route('/index1')
def index1():
    return render_template('index1.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':  # 注册发送的请求为POST请求
        username = request.form['username']
        password = request.form['password']
        if is_null(username, password):
            login_message = "温馨提示：账号和密码是必填"
            return render_template('login.html', message=login_message)
        elif is_existed(username, password):
            return render_template('index.html', username=username)
        elif exist_user(username):
            login_message = "温馨提示：密码错误，请输入正确密码"
            return render_template('login.html', message=login_message)
        else:
            login_message = "温馨提示：不存在该用户，请先注册"
            return render_template('login.html', message=login_message)
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if is_null(username, password):
                return jsonify({'success': False, 'error': '温馨提示：账号和密码是必填'})
            elif exist_user(username):
                return jsonify({'success': False, 'error': '温馨提示：用户已存在，请直接登录'})
            else:
                add_user(request.form['username'], request.form['password'])
                return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    return render_template('register.html')


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using {device} device")

# 模型路径
DETECT_MODEL_PATH = 'weights/detect.pt'
REC_MODEL_PATH = 'weights/plate_rec_color.pth'
CAR_REC_MODEL_PATH = 'weights/car_rec_color.pth'
IMG_SIZE = 384

# 加载模型
detect_model = load_model(DETECT_MODEL_PATH, device)
rec_model = init_model(device,REC_MODEL_PATH)
car_rec_model = init_car_rec_model(CAR_REC_MODEL_PATH, device)

# 设置上传和输出目录
UPLOAD_FOLDER = './static/uploads'
OUTPUT_FOLDER = './static/output'
CACHELOADS_FOLDER = './static/cacheloads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['CACHELOADS_FOLDER'] = CACHELOADS_FOLDER

# 确保上传和输出目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHELOADS_FOLDER, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 检查文件类型
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/traffic_analysis')
def traffic_analysis():
    return render_template('traffic_analysis.html')

@app.route('/video_processing', methods=['GET', 'POST'])
def video_processing():
    if request.method == 'POST':
        # 检查是否存在视频文件
        if 'video_file' not in request.files:
            return render_template('video_processing.html', error='No video file provided'), 400

        video_file = request.files['video_file']

        # 检查视频文件是否为空
        if video_file.filename == '':
            return render_template('video_processing.html', error='No video file selected'), 400

        # 获取JSON文件或路径
        json_file = request.files.get('json_file')
        json_path = request.form.get('json_path')

        # 保存上传的视频文件
        video_filename = secure_filename(video_file.filename)
        video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

        # 获取其他参数
        model_weights = request.form.get('model_weights', 'yolov8x.pt')
        device = request.form.get('device', 'cpu')
        confidence_threshold = float(request.form.get('confidence_threshold', 0.3))
        iou_threshold = float(request.form.get('iou_threshold', 0.7))
        classes_to_track = [int(x.strip()) for x in request.form.get('classes_to_track', '2, 5, 6, 7').split(',')]
        receiver_email = request.form.get('receiver_email')
        print('receiver_email:', receiver_email)

        processed_video_path = traffic_video(
            os.path.join(app.config['UPLOAD_FOLDER'], video_filename),
            json_file,
            json_path,
            model_weights, device, confidence_threshold, iou_threshold, classes_to_track,receiver_email
        )

        if processed_video_path is None:
            return render_template('video_processing.html', error='No JSON file provided'), 400
        

        background_image_url = url_for('static', filename='111.jpg')

        video_name = secure_filename(video_file.filename)
        # 渲染视频播放页面,并传递处理后的视频路径
        return render_template('video_player.html', processed_video_path=processed_video_path, background_image_url=background_image_url,receiver_email=receiver_email,video_name=video_name)

    # 渲染文件上传表单
    return render_template('video_processing.html')

def get_video_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame
    cap.release()

@app.route('/process_video', methods=['POST'])
def process_video_annotation():
    if 'video' in request.files:
        video_file = request.files['video']
        filename = video_file.filename
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(video_path)

        frame_generator = get_video_frames(video_path)
        try:
            frame = next(frame_generator)
            frame_path = os.path.join(app.config['UPLOAD_FOLDER'], 'frame.jpg')
            cv2.imwrite(frame_path, frame)
            return jsonify({'image_path': f'/uploads/{os.path.basename(frame_path)}'})
        except StopIteration:
            return jsonify({'error': 'Failed to extract video frame'}), 400
    else:
        return jsonify({'error': 'No video file found'}), 400

@app.route('/compressed_json', methods=['POST'])
def compressed_json():
    if 'json_data' in request.json:
        json_data = request.json['json_data']
        json_str = json.dumps(json_data)
        compressed_data = gzip.compress(json_str.encode())
        encoded_data = base64.b64encode(compressed_data).decode()
        file_path = 'static/output/polygons.json'
        with open(file_path, 'wb') as f:
            f.write(compressed_data)
        response_data = {
            'status': 'success',
            'data': encoded_data,
            'path': file_path
        }
        return jsonify(response_data)
    else:
        return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400

counter = 0
@app.route('/save_data', methods=['POST'])
def save_data():
    global counter
    if 'image_data' in request.json and 'polygons' in request.json:
        image_data = request.json['image_data']
        polygons = request.json['polygons']
        print('Received polygons:', polygons)
        # 将多边形坐标四舍五入为整数
        polygons = [[[round(point[0]), round(point[1])] for point in polygon] for polygon in polygons]
        print('Rounded polygons:', polygons)

        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

        image_filename = f'annotated_image_{counter}.png'
        image_dir = 'static/output'
        image_path = os.path.join(image_dir, image_filename)

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        with open(image_path, 'wb') as f:
            f.write(image_bytes)

        json_filename = f'annotated_image_{counter}.json'
        json_path = os.path.join('static/output', json_filename)
        with open(json_path, 'w') as f:
            json.dump(polygons, f, indent=2)

        counter += 1

        return jsonify({'status': 'success', 'image_path': image_path, 'json_path': json_path})
    else:
        return jsonify({'status': 'error', 'error': 'No image data or polygon data provided'}), 400

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download_video/<path:video_path>', methods=['GET'])
def download_video(video_path):
    file_path = os.path.join(app.root_path, video_path)
    if not os.path.isfile(file_path):
        return render_template('video_processing.html', error='File not found'), 404

    return send_file(file_path, as_attachment=True)

@app.route('/video_feed')
def video_feed():
    processed_video_path = request.args.get('processed_video_path')
    if not processed_video_path:
        return Response('No processed video file found', status=404)

    video = cv2.VideoCapture(processed_video_path)

    def generate_frames():
        while True:
            success, frame = video.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/image_upload')
def upload_image():
    """显示图像上传页面,并可选地显示上传的图像"""
    image_name = request.args.get('image', None)
    return render_template('image_upload.html', image=image_name)



# 创建一个队列来存储处理过的帧
frame_queue = Queue()
video_playing = False

@socketio.on('disconnect', namespace='/')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('connect', namespace='/')
def handle_connect():
    print('Client connected')

@socketio.on('start_video', namespace='/')
def start_video_processing( message):
    print("Received 'start_video' event")  
    print("Data: ", message['data'])
    global video_playing
    video_playing = True
    if video_playing:
        video_upload()

@app.route('/upload_image', methods=['POST'])
def upload_image_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + "_" + filename
        cachepath = os.path.join(app.config['CACHELOADS_FOLDER'], unique_filename)
        file.save(cachepath)
        
        # 读取上传的图像
        img = cv2.imread(cachepath)
        
        # 执行车牌识别
        detect_Recognition_plate(detect_model, img, device, rec_model, IMG_SIZE, car_rec_model)
        recognition_results = detect_Recognition_plate(detect_model, img, device, rec_model, IMG_SIZE, car_rec_model)
        print('recognition_result:', recognition_results)
        if recognition_results:
            for result in recognition_results:
                # 只有当对象是 NumPy 数组时才调用 .item()
                if isinstance(result['score'], np.ndarray):
                    result['score'] = result['score'].item()
                # 对于 color_conf,您可以直接将其赋值,因为它已经是 float 类型
                if 'color_conf' in result and isinstance(result['color_conf'], np.ndarray):
                    result['color_conf'] = result['color_conf'].item()
            
            print('result:', result)
        else:
            print('No recognition results')


        
        # 在原始图像上绘制识别结果
        processed_img = draw_result(img, recognition_results)
        
        # 保存处理后的图像
        processed_filename = "processed_" + unique_filename
        processed_filepath = os.path.join(app.config['OUTPUT_FOLDER'], processed_filename)
        cv2.imwrite(processed_filepath, processed_img)
        
        # 返回识别结果和处理后的图像的URL
        processed_img_url = url_for('uploaded_file', filename=processed_filename, _external=True)
        return jsonify({'results': recognition_results, 'processed_img_url': processed_img_url})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/output/<path:filename>')
def processed_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/video_upload', methods=['POST'])
def upload_video_file():
    print("开始处理上传的视频文件...")
    global cachepath, filename
    # request.files是一个字典,包含上传的文件
    if 'video' not in request.files:
        # 如果没有上传文件,则重定向到当前页面
        return redirect(request.url)
    file = request.files['video']
    if file.filename == '':
        return redirect(request.url)

    if file:
        print("找到上传的视频文件: " + file.filename)
        filename = secure_filename(file.filename)
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        cachepath = os.path.join(CACHELOADS_FOLDER, filename)
        file.save(cachepath)
        print("文件已保存至：", filepath)
        
        # 启动一个新线程来处理视频
        video_thread = threading.Thread(target=process_video, args=(cachepath, filename))
        print("开始处理视频文件...")
        video_thread.start()
        return render_template('video_upload.html', video=filename)

    return redirect(request.url)


video_processing = False
@app.route('/video_upload', methods=['GET', 'POST'])
def video_upload():
    global video_processing
    video_processing = True

    if request.method == 'POST':
        print("开始处理上传的视频文件...")
        return upload_video_file()
    # GET 请求,显示上传视频文件的页面
    print("get请求...")
    return render_template('video_upload.html')

frame_counter = 0  # 将计数器移到函数外部作为全局变量
def process_video(video_path, filename):
    global video_processing, frame_counter
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():  
        return "视频文件无法打开", 400
    
    
    ret, frame = cap.read()
    processed_filename = 'processed_' + filename
    out_filepath = os.path.join(OUTPUT_FOLDER, processed_filename)
    print('frame:', frame)
    print('frame.shape:', frame.shape)
    out = cv2.VideoWriter(out_filepath, cv2.VideoWriter_fourcc(*'mp4v'), 30, (frame.shape[1], frame.shape[0]))


    
    while video_processing:
        ret, frame = cap.read()  # 移动到循环内部
        if not ret:
            break
        # print("Frame read successfully")
        frame_counter += 1
        # 处理每一帧
        dict_list = detect_Recognition_plate(detect_model, frame, device, rec_model, IMG_SIZE, car_rec_model)
        processed_frame = draw_result(frame, dict_list)
        # 将处理后的帧写入输出视频文件
        out.write(processed_frame)

        # 将处理后的帧编码为JPEG格式,然后发送到前端
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        img_str = base64.b64encode(buffer).decode()
        
        socketio.emit('frame_count', f"第{frame_counter}帧识别成功,已成功发送", namespace='/')
        print(f"第{frame_counter}帧识别成功,已成功发送")
        socketio.emit('image data', {'frame_count': frame_counter, 'image': img_str}, namespace='/')

        socketio.sleep(0.1)  # 控制发送频率
        # 将车牌信息和处理后的帧放入队列
        for result in dict_list:
            plate_info =""
            if 'plate_no' not in result:
                continue
            plate_info = f"车牌号码: {result['plate_no']}"
            if 'plate_color' in result:
                plate_info += f", 车牌颜色: {result['plate_color']}"
            if 'class_type' in result:
                plate_info += f", 车牌类型: {result['class_type']}"
            if 'color' in result:
                plate_info += f", 车辆颜色: {result['color']}"
            if 'score' in result:
                plate_info += f", 置信度: {result['score'].item():.2f}"
            if plate_info:
                print(plate_info)
                frame_queue.put((plate_info, processed_frame))
                print("一帧已处理并添加到队列")

       #  frame_counter = 0  # 用于给每个帧的文件名编号
        output_dir = CACHELOADS_FOLDER  # 存储帧的目录
        os.makedirs(output_dir, exist_ok=True)  # 确保目录存在
        print('开始取数据发送到前端...')

        # 每隔一段时间从队列中取出数据并发送到前端
        while not frame_queue.empty():
            plate_info, processed_frame = frame_queue.get()
            print("从队列中取出一帧")
            socketio.emit('plate info', plate_info, namespace='/')
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            if ret:
                img_str = base64.b64encode(buffer).decode()
                print('发送数据到前端...\n')
                # socketio.emit('image data', img_str, namespace='/video_upload')

                # 保存帧到本地文件
                frame_filename = os.path.join(output_dir, f'frame_{frame_counter}.jpg')
                cv2.imwrite(frame_filename, processed_frame)
                frame_counter += 1

            socketio.sleep(0.1)  # 控制发送频率
        
    cap.release()
    out.release()

@socketio.on('clear_video', namespace='/')
def handle_clear_video():
    global video_processing
    video_processing = False

@app.route('/live_camera')
def live_camera():
    """显示实时摄像头视频流页面"""
    return render_template('live_camera.html')

def gen_frames():
    """生成摄像头视频流的帧,以供流式响应,并实时处理每一帧"""
    cap = cv2.VideoCapture(0)  # 创建视频捕获对象
    
    # 设置摄像头参数以提高清晰度
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    frame_count = 0
    while True:
        success, frame = cap.read()  # 从摄像头读取一帧
        if not success:
            print("错误：无法从摄像头读取图像")
            break
        else:
            frame_count += 1
            # 每10帧显示一次调试信息，避免控制台输出过多
            if frame_count % 10 == 0:
                print(f"处理第{frame_count}帧图像, 尺寸: {frame.shape}")
            
            # 记录识别开始时间
            start_time = time.time()
            
            # 对当前帧进行处理
            try:
                dict_list = detect_Recognition_plate(detect_model, frame, device, rec_model, IMG_SIZE, car_rec_model)
                # 显示识别结果
                if dict_list:
                    print(f"检测到{len(dict_list)}个对象:")
                    for idx, obj in enumerate(dict_list):
                        if 'plate_no' in obj:
                            print(f"  {idx+1}. 车牌号: {obj.get('plate_no', '未知')}, 类型: {obj.get('class_type', '未知')}, 颜色: {obj.get('plate_color', '未知')}, 置信度: {obj.get('score', 0):.2f}")
                        elif 'car_color' in obj:
                            print(f"  {idx+1}. 车辆颜色: {obj.get('car_color', '未知')}, 置信度: {obj.get('color_conf', 0):.2f}")
                else:
                    # 每30帧输出一次未检测到信息，避免过多输出
                    if frame_count % 30 == 0:
                        print("未检测到车牌或车辆")
                
                # 显示处理耗时
                processing_time = time.time() - start_time
                if frame_count % 10 == 0:
                    print(f"处理耗时: {processing_time:.4f}秒")
                
                # 在图像上显示调试信息
                cv2.putText(frame, f"FPS: {1/processing_time:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # 假设 draw_result 修改帧以显示结果
                processed_frame = draw_result(frame, dict_list)
            except Exception as e:
                print(f"识别过程发生错误: {str(e)}")
                processed_frame = frame
                # 在图像上显示错误信息
                cv2.putText(processed_frame, f"Error: {str(e)}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 将处理后的帧编码为JPEG格式,然后发送
            ret, buffer = cv2.imencode('.jpg', processed_frame)  # 注意这里使用 processed_frame
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
@app.route('/live_video_feed')
def live_video_feed():
    """路由到实时摄像头视频流。在HTML中用作<img>标签的源"""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print('http://127.0.0.1:5000')
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)