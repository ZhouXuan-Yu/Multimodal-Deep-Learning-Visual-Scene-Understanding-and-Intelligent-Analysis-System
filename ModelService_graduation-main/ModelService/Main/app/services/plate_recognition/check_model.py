"""
模型检查工具，用于查看模型文件结构
"""
import os
import torch
import sys

def print_model_structure(model_path):
    """打印模型文件结构"""
    print(f"\n正在检查模型文件: {model_path}")
    
    if not os.path.exists(model_path):
        print(f"错误: 模型文件不存在: {model_path}")
        return
    
    # 加载模型文件
    try:
        checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
        print(f"模型文件加载成功，大小: {os.path.getsize(model_path)/1024:.2f} KB")
        
        # 检查模型文件类型
        if isinstance(checkpoint, dict):
            print("模型文件是字典结构")
            
            # 打印顶级键
            print("\n顶级键:")
            for key in checkpoint.keys():
                print(f"  - {key}")
            
            # 如果有state_dict，打印其结构
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
                print("\n状态字典(state_dict)中的键:")
                for key in state_dict.keys():
                    tensor = state_dict[key]
                    print(f"  - {key}: {tensor.shape}")
            
            # 如果有cfg，打印其结构
            if 'cfg' in checkpoint:
                cfg = checkpoint['cfg']
                print("\n配置(cfg)内容:")
                print(cfg)
                
        else:
            print("模型文件是直接的状态字典(state_dict)")
            
            # 打印状态字典中的键
            print("\n状态字典中的键:")
            for key in checkpoint.keys():
                tensor = checkpoint[key]
                print(f"  - {key}: {tensor.shape}")
    
    except Exception as e:
        print(f"模型文件检查出错: {str(e)}")

if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    weights_dir = os.path.join(script_dir, "weights")
    
    # 设置要检查的模型文件
    model_path = os.path.join(weights_dir, "plate_rec_color.pth")
    
    # 如果命令行传入了模型路径，则使用命令行参数
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    
    # 执行检查
    print_model_structure(model_path)
