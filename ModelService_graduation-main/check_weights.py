import torch
import os

def check_weight_file(weight_path):
    print(f"检查权重文件: {weight_path}")
    
    # 加载权重文件
    data = torch.load(weight_path, map_location='cpu')
    
    # 输出文件基本信息
    print(f"文件类型: {type(data)}")
    
    if isinstance(data, dict):
        print(f"包含的键: {list(data.keys())}")
        
        if 'state_dict' in data:
            state_dict = data['state_dict']
            print("\n状态字典前10个键:")
            for i, key in enumerate(list(state_dict.keys())[:10]):
                print(f"{i+1}. {key}: {state_dict[key].shape}")
                
            # 特定于车牌颜色识别的关键层
            print("\n关键层形状:")
            key_layers = ['conv1.weight', 'conv1.bias', 'bn1.weight', 'bn1.bias', 
                         'color_classifier.weight', 'newCnn.weight', 'newCnn.bias']
            
            for layer in key_layers:
                if layer in state_dict:
                    print(f"{layer}: {state_dict[layer].shape}")
                else:
                    print(f"{layer}: 不存在")
        
        if 'cfg' in data:
            print(f"\n配置: {data['cfg']}")
    else:
        print("权重文件不是字典格式")

# 主函数
if __name__ == "__main__":
    # 检查车牌颜色识别模型
    plate_color_path = r"D:\Desktop\ModelService_graduation-main\ModelService\Main\app\services\plate_recognition\weights\plate_rec_color.pth"
    check_weight_file(plate_color_path)
    
    print("\n" + "-"*50 + "\n")
    
    # 检查车辆颜色识别模型
    car_color_path = r"D:\Desktop\ModelService_graduation-main\ModelService\Main\app\services\plate_recognition\weights\car_rec_color.pth"
    check_weight_file(car_color_path)
