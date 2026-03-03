'''
车辆识别，可以独立运行，也可以作为模块导入
'''
import argparse
import time
import os
import cv2
import torch
from numpy import random
import copy
import numpy as np
from models.experimental import attempt_load
from utilss.datasets import letterbox
from utilss.general import check_img_size, non_max_suppression_face, scale_coords
from utilss.torch_utils import time_synchronized
from utilss.cv_puttext import cv2ImgAddText
from plate_recognition.plate_rec import get_plate_result,allFilePath,init_model,cv_imread
# from plate_recognition.plate_cls import cv_imread
from plate_recognition.double_plate_split_merge import get_split_merge
from plate_recognition.color_rec import plate_color_rec,init_color_model
from car_recognition.car_rec import init_car_rec_model,get_color_and_score

clors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(0,255,255)]
danger=['危','险']
object_color=[(0,255,255),(0,255,0),(255,255,0)]
class_type=['单层车牌','双层车牌','汽车']
def order_points(pts):                   #四个点安好左上 右上 右下 左下排列
    rect = np.zeros((4, 2), dtype = "float32")
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):                       #透视变换得到车牌小图
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype = "float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def load_model(weights, device):
    model = attempt_load(weights, map_location=device)  # load FP32 model
    return model

def scale_coords_landmarks(img1_shape, coords, img0_shape, ratio_pad=None):  #返回到原图坐标
    # Rescale coords (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])  # gain  = old / new
        pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2  # wh padding
    else:
        gain = ratio_pad[0][0]
        pad = ratio_pad[1]

    coords[:, [0, 2, 4, 6]] -= pad[0]  # x padding
    coords[:, [1, 3, 5, 7]] -= pad[1]  # y padding
    coords[:, :8] /= gain
    #clip_coords(coords, img0_shape)
    coords[:, 0].clamp_(0, img0_shape[1])  # x1
    coords[:, 1].clamp_(0, img0_shape[0])  # y1
    coords[:, 2].clamp_(0, img0_shape[1])  # x2
    coords[:, 3].clamp_(0, img0_shape[0])  # y2
    coords[:, 4].clamp_(0, img0_shape[1])  # x3
    coords[:, 5].clamp_(0, img0_shape[0])  # y3
    coords[:, 6].clamp_(0, img0_shape[1])  # x4
    coords[:, 7].clamp_(0, img0_shape[0])  # y4
    # coords[:, 8].clamp_(0, img0_shape[1])  # x5
    # coords[:, 9].clamp_(0, img0_shape[0])  # y5
    return coords

def get_plate_rec_landmark(img, xyxy, conf, landmarks, class_num,device,plate_rec_model,car_rec_model):
    h,w,c = img.shape
    result_dict={}
    x1 = int(xyxy[0])
    y1 = int(xyxy[1])
    x2 = int(xyxy[2])
    y2 = int(xyxy[3])
    landmarks_np=np.zeros((4,2))
    rect=[x1,y1,x2,y2]
    
    if int(class_num) ==2:
        # 
        car_roi_img = img[y1:y2,x1:x2]
        car_color,color_conf=get_color_and_score(car_rec_model,car_roi_img,device)
        result_dict['class_type']=class_type[int(class_num)]
        result_dict['rect']=rect                      #车辆roi
        result_dict['score']=conf                     #车牌区域检测得分
        result_dict['object_no']=int(class_num)
        result_dict['car_color']=car_color
        result_dict['color_conf']=color_conf
        return result_dict
    
    for i in range(4):
        point_x = int(landmarks[2 * i])
        point_y = int(landmarks[2 * i + 1])
        landmarks_np[i]=np.array([point_x,point_y])

    class_label= int(class_num)  #车牌的的类型0代表单牌，1代表双层车牌
    roi_img = four_point_transform(img,landmarks_np)   #透视变换得到车牌小图
    if class_label:        #判断是否是双层车牌，是双牌的话进行分割后然后拼接
        roi_img=get_split_merge(roi_img)
    plate_number ,plate_color= get_plate_result(roi_img,device,plate_rec_model)                 #对车牌小图进行识别,得到颜色和车牌号
    for dan in danger:                                                           #只要出现‘危’或者‘险’就是危险品车牌
        if dan in plate_number:
            plate_number='危险品'
    # cv2.imwrite("roi.jpg",roi_img)
    result_dict['class_type']=class_type[class_label]
    result_dict['rect']=rect                      #车牌roi区域
    result_dict['landmarks']=landmarks_np.tolist() #车牌角点坐标
    result_dict['plate_no']=plate_number   #车牌号
    result_dict['roi_height']=roi_img.shape[0]  #车牌高度
    result_dict['plate_color']=plate_color   #车牌颜色
    result_dict['object_no']=class_label   #单双层 0单层 1双层
    result_dict['score']=conf           #车牌区域检测得分
    return result_dict



def detect_Recognition_plate(model, orgimg, device, plate_rec_model, img_size, car_rec_model=None):
    # 设置更低的置信度阈值以捕获更多可能的车牌
    conf_thres = 0.4  # 降低置信度阈值，增加检测敏感度
    iou_thres = 0.5
    dict_list = []
    
    print("\n---------- 车牌识别开始 ----------")
    print(f"输入图像形状: {orgimg.shape}")
    
    # 检查图像质量
    gray = cv2.cvtColor(orgimg, cv2.COLOR_BGR2GRAY)
    blurness = cv2.Laplacian(gray, cv2.CV_64F).var()
    print(f"图像清晰度指标: {blurness:.2f} (数值越大越清晰)")
    
    # 保存检测用的输入图像以便分析
    debug_dir = "debug_images"
    os.makedirs(debug_dir, exist_ok=True)
    debug_filename = os.path.join(debug_dir, f"input_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
    cv2.imwrite(debug_filename, orgimg)
    print(f"保存输入图像至: {debug_filename}")
    
    img0 = copy.deepcopy(orgimg)
    assert orgimg is not None, 'Image Not Found'
    h0, w0 = orgimg.shape[:2]  # orig hw
    
    # 图像预处理 - 调整大小
    r = img_size / max(h0, w0)  # resize image to img_size
    if r != 1:  # always resize down, only resize up if training with augmentation
        interp = cv2.INTER_AREA if r < 1 else cv2.INTER_LINEAR
        img0 = cv2.resize(img0, (int(w0 * r), int(h0 * r)), interpolation=interp)
        print(f"调整图像大小: 原始尺寸={h0}x{w0}, 调整后尺寸={img0.shape[0]}x{img0.shape[1]}")

    # 图像预处理 - 检查并调整输入尺寸
    imgsz = check_img_size(img_size, s=model.stride.max())  # check img_size
    print(f"模型输入尺寸: {imgsz}")

    # 图像预处理 - letterbox填充
    img = letterbox(img0, new_shape=imgsz)[0]
    print(f"填充后图像形状: {img.shape}")
    
    # 转换为模型输入格式
    img = img[:, :, ::-1].transpose(2, 0, 1).copy()  # BGR to RGB, to 3x416x416

    # 开始推理计时
    t0 = time.time()

    # 转为Tensor
    img = torch.from_numpy(img).to(device)
    img = img.float()  # uint8 to fp16/32
    img /= 255.0  # 0 - 255 to 0.0 - 1.0
    if img.ndimension() == 3:
        img = img.unsqueeze(0)
    print(f"输入Tensor形状: {img.shape}")

    # 推理
    t1 = time_synchronized()
    try:
        pred = model(img)[0]
        t2 = time_synchronized()
        print(f"模型推理耗时: {(t2-t1)*1000:.2f} ms")
    except Exception as e:
        print(f"模型推理错误: {e}")
        return []

    # 应用NMS
    try:
        pred = non_max_suppression_face(pred, conf_thres, iou_thres)
        print(f"NMS后检测数量: {len(pred[0]) if len(pred) > 0 else 0}")
    except Exception as e:
        print(f"NMS处理错误: {e}")
        return []

    # 如果没有检测到任何目标
    if len(pred[0]) == 0:
        print("没有检测到任何车牌或车辆，尝试调整置信度阈值或改善图像质量")
        # 尝试增强图像并显示
        enhanced = cv2.convertScaleAbs(orgimg, alpha=1.5, beta=0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        lab[:,:,0] = clahe.apply(lab[:,:,0])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        cv2.imwrite(os.path.join(debug_dir, f"enhanced_{time.strftime('%Y%m%d_%H%M%S')}.jpg"), enhanced)
        print("已保存增强后的图像以供分析")
        return []

    # 处理检测结果
    for i, det in enumerate(pred):  # detections per image
        if len(det):
            print(f"检测到 {len(det)} 个可能的车牌或车辆")
            
            # 重新缩放边界框
            det[:, :4] = scale_coords(img.shape[2:], det[:, :4], orgimg.shape).round()
            
            # 打印各类别数量
            for c in det[:, -1].unique():
                n = (det[:, -1] == c).sum()  # detections per class
                print(f"类别 {int(c)} 检测数量: {n}")

            # 重新缩放关键点坐标
            det[:, 5:13] = scale_coords_landmarks(img.shape[2:], det[:, 5:13], orgimg.shape).round()

            # 逐个处理检测结果
            for j in range(det.size()[0]):
                try:
                    xyxy = det[j, :4].view(-1).tolist()
                    conf = det[j, 4].cpu().numpy()
                    landmarks = det[j, 5:13].view(-1).tolist()
                    class_num = det[j, 13].cpu().numpy()
                    
                    print(f"检测 #{j+1}: 类别={int(class_num)}, 置信度={conf:.4f}")
                    print(f"  位置: x1={xyxy[0]:.1f}, y1={xyxy[1]:.1f}, x2={xyxy[2]:.1f}, y2={xyxy[3]:.1f}")
                    
                    # 保存检测到的区域
                    roi = orgimg[int(xyxy[1]):int(xyxy[3]), int(xyxy[0]):int(xyxy[2])]
                    if roi.size > 0:
                        roi_filename = os.path.join(debug_dir, f"roi_{j}_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
                        cv2.imwrite(roi_filename, roi)
                        print(f"  ROI已保存: {roi_filename}")
                    
                    # 识别车牌
                    result_dict = get_plate_rec_landmark(orgimg, xyxy, conf, landmarks, class_num, device, plate_rec_model, car_rec_model)
                    
                    # 打印识别结果
                    if 'plate_no' in result_dict:
                        print(f"  识别结果: 车牌={result_dict['plate_no']}, 颜色={result_dict.get('plate_color', '未知')}")
                    elif 'car_color' in result_dict:
                        print(f"  识别结果: 车辆颜色={result_dict['car_color']}")
                    else:
                        print("  识别结果: 未能识别车牌")
                    
                    dict_list.append(result_dict)
                except Exception as e:
                    print(f"处理检测结果 #{j+1} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print("处理后没有检测结果")
    
    # 计算总耗时
    total_time = time.time() - t0
    print(f"车牌识别总耗时: {total_time*1000:.2f} ms")
    print("---------- 车牌识别结束 ----------\n")
    
    return dict_list

def draw_result(orgimg, dict_list, highlight_plate=None):
    """绘制结果，可选择只高亮目标车牌
    
    参数:
        orgimg: 原始图像
        dict_list: 识别结果列表
        highlight_plate: 需要高亮的目标车牌号，如果不为None，则只显示该车牌
        
    返回:
        处理后的图像
    """
    result_str =""
    draw_all = highlight_plate is None  # 是否绘制所有车牌（没有指定目标车牌时）
    
    # 创建结果图像副本
    result_img = orgimg.copy()
    
    # 找到匹配的目标车牌（如果有的话）
    target_result = None
    if highlight_plate:
        for result in dict_list:
            if 'plate_no' in result and result['plate_no'] == highlight_plate:
                target_result = result
                break
    
    # 处理所有检测结果
    for result in dict_list:
        # 是否绘制当前结果
        should_draw = draw_all or (result == target_result)
        
        # 如果只画目标车牌但当前不是目标，则跳过
        if not should_draw:
            continue
            
        rect_area = result['rect']
        object_no = result['object_no']
        
        # 车牌（对象类型0和1）
        if not object_no == 2:    
            x,y,w,h = rect_area[0],rect_area[1],rect_area[2]-rect_area[0],rect_area[3]-rect_area[1]
            padding_w = 0.05*w
            padding_h = 0.11*h
            rect_area[0]=max(0,int(x-padding_w))
            rect_area[1]=max(0,int(y-padding_h))
            rect_area[2]=min(result_img.shape[1],int(rect_area[2]+padding_w))
            rect_area[3]=min(result_img.shape[0],int(rect_area[3]+padding_h))

            height_area = int(result['roi_height']/2)
            landmarks=result['landmarks']
            result_p = result['plate_no']
            plate_color = result['plate_color']
            class_type = result['class_type']

            # 构建显示文本
            if result['object_no']==0:  # 单层
                result_p+=" "+result['plate_color']
            else:                       # 双层
                result_p+=" "+result['plate_color']+"双层"
            result_str+=result_p+" "
            
            # 绘制关键点
            for i in range(4):
                cv2.circle(result_img, (int(landmarks[i][0]), int(landmarks[i][1])), 5, clors[i], -1)
            
            # 添加文字标注
            if len(result)>=1:
                if "危险品" in result_p:  # 如果是危险品车牌，文字就画在下面
                    result_img=cv2ImgAddText(result_img,result_p,rect_area[0],rect_area[3],(0,255,0),height_area)
                else:
                    result_img=cv2ImgAddText(result_img,result_p,rect_area[0]-height_area,rect_area[1]-height_area-10,(0,255,0),height_area)
        # 车辆（对象类型2）
        else:
            # 如果只显示目标车牌，且当前不是目标车牌相关的车辆，则跳过
            if highlight_plate and target_result is None:
                continue
                
            height_area=int((rect_area[3]-rect_area[1])/20)
            car_color = result['car_color']
            car_color_str="车辆颜色:"
            car_color_str+=car_color
            result_img=cv2ImgAddText(result_img,car_color_str,rect_area[0],rect_area[1],(0,255,0),height_area)

        # 判断是否需要高亮显示
        color = object_color[object_no]
        thickness = 2
        
        # 高亮目标车牌
        is_target = False
        if highlight_plate and object_no in [0, 1] and 'plate_no' in result and result['plate_no'] == highlight_plate:
            color = (0, 0, 255)  # 红色
            thickness = 3
            is_target = True
            
            # 添加TARGET标记
            cv2.putText(result_img, "TARGET", (rect_area[0], rect_area[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
            # 如果是目标车牌，额外绘制更醒目的标记
            cv2.rectangle(result_img, 
                        (rect_area[0]-2, rect_area[1]-2), 
                        (rect_area[2]+2, rect_area[3]+2), 
                        (0, 100, 255), 1)  # 外层橙色边框
        
        # 绘制矩形框 - 只有目标车牌或者在未指定目标时才绘制
        if not highlight_plate or is_target:
            cv2.rectangle(result_img, (rect_area[0], rect_area[1]), (rect_area[2], rect_area[3]), color, thickness)
    
    return result_img
 

def get_second(capture):
    if capture.isOpened():
        rate = capture.get(5)   # 帧速率
        FrameNumber = capture.get(7)  # 视频文件的帧数
        duration = FrameNumber/rate  # 帧速率/视频总帧数 是时间，除以60之后单位是分钟
        return int(rate),int(FrameNumber),int(duration)    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--detect_model', nargs='+', type=str, default='weights/detect.pt', help='model.pt path(s)')  #检测模型
    parser.add_argument('--rec_model', type=str, default='weights/plate_rec_color.pth', help='model.pt path(s)')#车牌识别+车牌颜色识别模型
    parser.add_argument('--car_rec_model',type=str,default='weights/car_rec_color.pth',help='car_rec_model') #车辆识别模型
    parser.add_argument('--image_path', type=str, default='imgs', help='source') 
    parser.add_argument('--img_size', type=int, default=384, help='inference size (pixels)')
    parser.add_argument('--output', type=str, default='result1', help='source') 
    parser.add_argument('--video', type=str, default='', help='source') 
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # device =torch.device("cpu")
    opt = parser.parse_args()
    print(opt)
    save_path = opt.output
    count=0
    if not os.path.exists(save_path):
        os.mkdir(save_path)

    detect_model = load_model(opt.detect_model, device)  #初始化检测模型
    plate_rec_model=init_model(device,opt.rec_model)      #初始化识别模型
    car_rec_model = init_car_rec_model(opt.car_rec_model,device) #初始化车辆识别模型
    #算参数量
    total = sum(p.numel() for p in detect_model.parameters())
    total_1 = sum(p.numel() for p in plate_rec_model.parameters())
    print("detect params: %.2fM,rec params: %.2fM" % (total/1e6,total_1/1e6))
    
    time_all = 0
    time_begin=time.time()
    if not opt.video:     #处理图片
        if not os.path.isfile(opt.image_path):            #目录
            file_list=[]
            allFilePath(opt.image_path,file_list)
            for img_path in file_list:
                
                print(count,img_path,end=" ")
                time_b = time.time()
                img =cv_imread(img_path)
                
                if img is None:
                    continue
                if img.shape[-1]==4:
                    img=cv2.cvtColor(img,cv2.COLOR_BGRA2BGR)
                # detect_one(model,img_path,device)
                dict_list=detect_Recognition_plate(detect_model, img, device,plate_rec_model,opt.img_size,car_rec_model)
                # print(dict_list)
                ori_img=draw_result(img,dict_list)
                img_name = os.path.basename(img_path)
                save_img_path = os.path.join(save_path,img_name)
                time_e=time.time()
                time_gap = time_e-time_b
                if count:
                    time_all+=time_gap
                cv2.imwrite(save_img_path,ori_img)
                count+=1
        else:                                          #单个图片
                print(count,opt.image_path,end=" ")
                img =cv_imread(opt.image_path)
                if img.shape[-1]==4:
                    img=cv2.cvtColor(img,cv2.COLOR_BGRA2BGR)
                # detect_one(model,img_path,device)
                dict_list=detect_Recognition_plate(detect_model, img, device,plate_rec_model,opt.img_size)
                ori_img=draw_result(img,dict_list)
                img_name = os.path.basename(opt.image_path)
                save_img_path = os.path.join(save_path,img_name)
                cv2.imwrite(save_img_path,ori_img)  
        print(f"sumTime time is {time.time()-time_begin} s, average pic time is {time_all/(len(file_list)-1)}")
        
    else:    #处理视频
        video_name = opt.video
        capture=cv2.VideoCapture(video_name)
        fourcc = cv2.VideoWriter_fourcc(*'MP4V') 
        fps = capture.get(cv2.CAP_PROP_FPS)  # 帧数
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 宽高
        out = cv2.VideoWriter('result.mp4', fourcc, fps, (width, height))  # 写入视频
        frame_count = 0
        fps_all=0
        rate,FrameNumber,duration=get_second(capture)
        if capture.isOpened():
            while True:
                t1 = cv2.getTickCount()
                frame_count+=1
                print(f"第{frame_count} 帧",end=" ")
                ret,img=capture.read()
                if not ret:
                    break
                # if frame_count%rate==0:
                img0 = copy.deepcopy(img)
                dict_list=detect_Recognition_plate(detect_model, img, device,plate_rec_model,opt.img_size,car_rec_model)
                ori_img=draw_result(img,dict_list)
                t2 =cv2.getTickCount()
                infer_time =(t2-t1)/cv2.getTickFrequency()
                fps=1.0/infer_time
                fps_all+=fps
                str_fps = f'fps:{fps:.4f}'
                
                cv2.putText(ori_img,str_fps,(20,20),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
                # cv2.imshow("haha",ori_img)
                # cv2.waitKey(1)
                out.write(ori_img)

                # current_time = int(frame_count/FrameNumber*duration)
                # sec = current_time%60
                # minute = current_time//60
                # for result_ in result_list:
                #     plate_no = result_['plate_no']
                #     if not is_car_number(pattern_str,plate_no):
                #         continue
                #     print(f'车牌号:{plate_no},时间:{minute}分{sec}秒')
                #     time_str =f'{minute}分{sec}秒'
                #     writer.writerow({"车牌":plate_no,"时间":time_str})
                # out.write(ori_img)
                
                
        else:
            print("失败")
        capture.release()
        out.release()
        cv2.destroyAllWindows()
        print(f"all frame is {frame_count},average fps is {fps_all/frame_count} fps")