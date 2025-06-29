#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time       : 2025/5/16 18:25
# @Author     : ZZ
# @File       : ImagePixel.py
# @Software   : PyCharm
import os
from PIL import Image
import shutil

def resize_images(source_folder, target_width=1040):
    """
    调整指定文件夹内所有图片的宽度为1040像素，保持比例不变。
    并将调整后的图片存储到新文件夹中，新文件夹结构与原文件夹结构一致。
    """
    # 创建目标文件夹路径
    target_folder = source_folder + "-1040"
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"Created target folder: {target_folder}")

    # 遍历源文件夹
    for root, dirs, files in os.walk(source_folder):
        print(f"Processing folder: {root}")
        # 计算目标路径
        relative_path = os.path.relpath(root, source_folder)
        target_subfolder = os.path.join(target_folder, relative_path)
        if not os.path.exists(target_subfolder):
            os.makedirs(target_subfolder)
            print(f"Created subfolder: {target_subfolder}")

        # 检测当前目录是否存在图片文件
        has_images = any(file_name.lower().endswith(('.png', '.jpg', '.jpeg')) for file_name in files)
        
        # 如果存在图片则创建空文件夹
        if has_images:
            # 修改：在目标文件夹路径创建空文件夹
            os.makedirs(os.path.join(target_subfolder, '500'), exist_ok=True)
            os.makedirs(os.path.join(target_subfolder, '详情'), exist_ok=True)
            print(f"Created empty folders in: {target_subfolder}")

        # 复制非图片文件夹结构
        for dir_name in dirs:
            source_dir_path = os.path.join(root, dir_name)
            target_dir_path = os.path.join(target_subfolder, dir_name)
            if not os.path.exists(target_dir_path):
                os.makedirs(target_dir_path)
                print(f"Created subfolder: {target_dir_path}")

        # 处理图片文件
        for file_name in files:
            source_file_path = os.path.join(root, file_name)
            target_file_path = os.path.join(target_subfolder, file_name)

            # 检查是否是图片文件（通过扩展名）
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    # 打开图片并调整大小
                    with Image.open(source_file_path) as img:
                        # 读取并应用 EXIF 元数据中的方向信息
                        if hasattr(img, '_getexif'):
                            exif = img._getexif()
                            if exif:
                                orientation = exif.get(0x0112)  # Orientation tag
                                if orientation == 3:
                                    img = img.rotate(180, expand=True)
                                elif orientation == 6:
                                    img = img.rotate(270, expand=True)
                                elif orientation == 8:
                                    img = img.rotate(90, expand=True)

                        # 调整图片大小
                        width, height = img.size
                        new_height = int(height * (target_width / width))
                        resized_img = img.resize((target_width, new_height), Image.Resampling.BILINEAR)

                        # 新增：转换为RGB模式以确保兼容JPEG格式
                        if resized_img.mode != 'RGB':
                            # 创建白色背景合并透明通道
                            bg = Image.new('RGB', resized_img.size, (255, 255, 255))
                            # 检查是否存在alpha通道
                            if resized_img.mode == 'RGBA':
                                bg.paste(resized_img, mask=resized_img.split()[3])
                            else:
                                bg.paste(resized_img)
                            resized_img = bg
                        # 保存图片，保留元数据
                        resized_img.save(target_file_path, quality=100, icc_profile=img.info.get('icc_profile'))
                        print(f"Resized and saved: {target_file_path}")
                except Exception as e:
                    print(f"Error processing {source_file_path}: {e}")
            else:
                # 如果不是图片文件，直接复制到目标文件夹
                shutil.copy2(source_file_path, target_file_path)
                print(f"Copied non-image file: {target_file_path}")

# 输入源文件夹路径
source_folder = input("请输入源文件夹路径：")
if not os.path.exists(source_folder):
    print("输入的文件夹路径不存在，请检查后重新输入！")
else:
    resize_images(source_folder)
    print("图片处理完成！")