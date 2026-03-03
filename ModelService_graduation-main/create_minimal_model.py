"""
创建最小化PyTorch模型文件
"""
import os
import torch
import numpy as np

# 确保目录存在
weights_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         'design-competition', 'weights')
if not os.path.exists(weights_dir):
    os.makedirs(weights_dir)
    print(f"已创建目录: {weights_dir}")

# 模型文件路径
model_file = os.path.join(weights_dir, 'detect.pt')

# 创建一个简单的模型类
class SimpleModel(torch.nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.conv = torch.nn.Conv2d(3, 1, 3, padding=1)
    
    def forward(self, x):
        return self.conv(x)

# 实例化模型
model = SimpleModel()

# 保存模型
print(f"创建模型文件: {model_file}")
torch.save({'model': model}, model_file)
print("模型文件创建成功")

# 验证文件是否存在
if os.path.exists(model_file):
    print(f"文件大小: {os.path.getsize(model_file) / 1024:.2f} KB")
else:
    print("错误: 文件创建失败")
