import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

# =================================================================
# Retinex-based Image Enhancement
# =================================================================
def singleScaleRetinex(img, sigma):
    """
    Single-scale Retinex algorithm
    """
    retinex = np.log10(img) - np.log10(cv2.GaussianBlur(img, (0, 0), sigma))
    return retinex

def multiScaleRetinex(img, sigma_list):
    """
    Multi-scale Retinex algorithm
    """
    retinex = np.zeros_like(img)
    for sigma in sigma_list:
        retinex += singleScaleRetinex(img, sigma)
    retinex = retinex / len(sigma_list)
    return retinex

def colorRestoration(img, alpha, beta):
    """
    Color restoration for Retinex
    """
    img_sum = np.sum(img, axis=2, keepdims=True)
    color_restoration = beta * (np.log10(alpha * img) - np.log10(img_sum + 1e-6))
    return color_restoration

def simplestColorBalance(img, low_clip, high_clip):
    """
    Simplest color balance algorithm
    """
    total = img.shape[0] * img.shape[1]
    for i in range(img.shape[2]):
        current_channel = img[:, :, i]
        unique, counts = np.unique(current_channel, return_counts=True)
        
        # Calculate cumulative distribution function
        current_cdf = np.cumsum(counts) / total
        
        # Find values for low and high cut
        low_bound = unique[np.searchsorted(current_cdf, low_clip)]
        high_bound = unique[np.searchsorted(current_cdf, 1 - high_clip)]
        
        # Apply intensity normalization
        img[:, :, i] = np.clip(current_channel, low_bound, high_bound)
        
        # Scale to [0, 255]
        img[:, :, i] = ((img[:, :, i] - low_bound) / (high_bound - low_bound)) * 255
    
    return img

def MSRCR(img, sigma_list=[15, 80, 250], G=5, b=25, alpha=125, beta=46, low_clip=0.01, high_clip=0.99):
    """
    Multi-scale Retinex with Color Restoration
    """
    img = np.float32(img) + 1.0
    
    # Multi-scale Retinex
    retinex = multiScaleRetinex(img, sigma_list)
    
    # Color restoration
    restoration = colorRestoration(img, alpha, beta)
    
    # Add results together
    msrcr = G * (retinex * restoration + b)
    
    # Scale result to [0, 255]
    msrcr = np.clip(msrcr, 0, 255)
    
    # Apply simplest color balance
    msrcr = simplestColorBalance(msrcr, low_clip, high_clip)
    
    return msrcr.astype(np.uint8)

# =================================================================
# Zero-DCE Algorithm
# =================================================================
class ZeroDCE(nn.Module):
    """
    Zero-Reference Deep Curve Estimation Network
    """
    def __init__(self):
        super(ZeroDCE, self).__init__()
        
        self.relu = nn.ReLU(inplace=True)
        self.e_conv1 = nn.Conv2d(3, 32, 3, 1, 1, bias=True)
        self.e_conv2 = nn.Conv2d(32, 32, 3, 1, 1, bias=True)
        self.e_conv3 = nn.Conv2d(32, 32, 3, 1, 1, bias=True)
        self.e_conv4 = nn.Conv2d(32, 32, 3, 1, 1, bias=True)
        self.e_conv5 = nn.Conv2d(32, 32, 3, 1, 1, bias=True)
        self.e_conv6 = nn.Conv2d(32, 32, 3, 1, 1, bias=True)
        self.e_conv7 = nn.Conv2d(32, 24, 3, 1, 1, bias=True)
        
    def forward(self, x):
        x1 = self.relu(self.e_conv1(x))
        x2 = self.relu(self.e_conv2(x1))
        x3 = self.relu(self.e_conv3(x2))
        x4 = self.relu(self.e_conv4(x3))
        x5 = self.relu(self.e_conv5(x4))
        x6 = self.relu(self.e_conv6(x5))
        x_r = torch.tanh(self.e_conv7(x6))
        
        r1, r2, r3, r4, r5, r6, r7, r8 = torch.split(x_r, 3, dim=1)
        
        x = x + r1 * (torch.pow(x, 2) - x)
        x = x + r2 * (torch.pow(x, 2) - x)
        x = x + r3 * (torch.pow(x, 2) - x)
        enhance_image_1 = x + r4 * (torch.pow(x, 2) - x)
        x = enhance_image_1 + r5 * (torch.pow(enhance_image_1, 2) - enhance_image_1)
        x = x + r6 * (torch.pow(x, 2) - x)
        x = x + r7 * (torch.pow(x, 2) - x)
        enhance_image = x + r8 * (torch.pow(x, 2) - x)
        
        return enhance_image

def apply_zero_dce(img, model=None):
    """
    Apply Zero-DCE algorithm to an image
    """
    # Convert to float tensor
    if isinstance(img, np.ndarray):
        img = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0
    
    if model is None:
        # Create model
        model = ZeroDCE().eval()
        # In a real implementation, you'd load pre-trained weights here
        # model.load_state_dict(torch.load('zero_dce_weights.pth'))
    
    # Process through model
    with torch.no_grad():
        enhanced = model(img)
    
    # Convert back to numpy
    enhanced = enhanced.clamp(0, 1).cpu().squeeze(0).numpy()
    enhanced = (enhanced.transpose(1, 2, 0) * 255.0).astype(np.uint8)
    
    return enhanced

# =================================================================
# EnlightenGAN-inspired Enhancement
# =================================================================
def apply_enlightengan_like(img):
    """
    Apply EnlightenGAN-inspired enhancement (simplified approximation)
    Note: This is a simplified approximation, not the actual EnlightenGAN
    """
    # Convert to LAB color space
    if isinstance(img, np.ndarray):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    else:
        # If PIL Image
        img_np = np.array(img)
        lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    
    # Split channels
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Adjust gamma on enhanced L channel
    gamma = 0.85
    cl_gamma = np.array(255 * (cl / 255) ** gamma, dtype=np.uint8)
    
    # Merge back
    enhanced_lab = cv2.merge((cl_gamma, a, b))
    
    # Convert back to original color space
    if isinstance(img, np.ndarray):
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    else:
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
    
    # Additional color enhancement
    if isinstance(img, np.ndarray):
        # BGR order for OpenCV
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.2, beta=10)
    else:
        # RGB order for PIL
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.2, beta=10)
    
    return enhanced

# =================================================================
# KinD-inspired Enhancement (Kindling the Darkness)
# =================================================================
def apply_kind_like(img):
    """
    Apply KinD-inspired enhancement (simplified approximation)
    Note: This is a simplified approximation, not the actual KinD model
    """
    if isinstance(img, np.ndarray):
        # Make a copy to avoid modifying the original
        img_copy = img.copy()
        
        # Decompose image (illumination estimation)
        gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)
        illum_map = cv2.GaussianBlur(gray, (71, 71), 0)
        illum_map = np.maximum(illum_map, 10) / 255.0
        
        # Normalize illumination
        illum_norm = (illum_map - np.min(illum_map)) / (np.max(illum_map) - np.min(illum_map) + 1e-6)
        illum_norm = np.power(illum_norm, 0.6)  # Gamma correction on illumination
        
        # Enhance details
        r, g, b = cv2.split(img_copy)
        r_enhanced = np.minimum(r * (1.2 / illum_norm), 255).astype(np.uint8)
        g_enhanced = np.minimum(g * (1.2 / illum_norm), 255).astype(np.uint8)
        b_enhanced = np.minimum(b * (1.2 / illum_norm), 255).astype(np.uint8)
        
        # Merge channels
        enhanced = cv2.merge([r_enhanced, g_enhanced, b_enhanced])
        
        # Apply final adjustments
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.1, beta=10)
        
        return enhanced
    else:
        # If PIL Image
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        enhanced = apply_kind_like(img_np)  # Recursive call with numpy array
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        return Image.fromarray(enhanced)

# =================================================================
# Combined Advanced Enhancement
# =================================================================
def advanced_enhance(img, method='retinex'):
    """
    Apply advanced enhancement methods to an image
    """
    if isinstance(img, str):
        # If image path is provided
        img = cv2.imread(img)
    
    if isinstance(img, np.ndarray):
        if method == 'retinex':
            enhanced = MSRCR(img)
        elif method == 'zero_dce':
            enhanced = apply_zero_dce(img)
        elif method == 'enlightengan':
            enhanced = apply_enlightengan_like(img)
        elif method == 'kind':
            enhanced = apply_kind_like(img)
        else:  # Default to retinex
            enhanced = MSRCR(img)
        
        # Return RGB if it's a numpy array (for consistency)
        if isinstance(enhanced, np.ndarray):
            if enhanced.ndim == 3 and enhanced.shape[2] == 3:
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                return Image.fromarray(enhanced)
        
        return enhanced
    elif isinstance(img, Image.Image):
        # Convert PIL Image to numpy array
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Apply enhancement
        enhanced = advanced_enhance(img_np, method)
        
        # Convert back to PIL Image
        if isinstance(enhanced, np.ndarray):
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
            return Image.fromarray(enhanced)
        return enhanced
    else:
        raise ValueError("Unsupported image type")
