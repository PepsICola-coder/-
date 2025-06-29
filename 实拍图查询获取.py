#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time       : 2025/6/11 0:35
# @Author     : ZZ
# @File       : 实拍图查询获取.py
# @Software   : PyCharm
import requests
import pandas as pd
import os
import re
# 新增随机延时（5-10秒）
import time
import random
#203624


def get_comment(goods_id,  save_path, zz):
    data = {
        'goods_id': goods_id,
        'page': '1',
    }
    ll = []
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.zhuangxiaozhuang.com',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    response = requests.post(
        'https://www.zhuangxiaozhuang.com/index.php?s=/index/goods/comment.html',
        headers=headers,
        data=data,
    )
    obj = response.json()
    #print(obj)
    if obj['data']['data']:
        img_urls  = obj['data']['data'][0]['images']
        # 创建保存目录
        os.makedirs(save_path, exist_ok=True)
        # 下载并保存所有图片
        for idx, url in enumerate(img_urls, 1):
            try:
                # 下载图片
                img_response = requests.get(url, headers=headers, timeout=10)
                img_response.raise_for_status()

                # 生成文件名（保留原始文件名）
                filename = zz + f"-P_{idx}.jpg"
                file_path = os.path.join(save_path, filename)

                # 处理文件名冲突
                counter = 1
                while os.path.exists(file_path):
                    base, ext = os.path.splitext(filename)
                    file_path = os.path.join(save_path, f"{base}_{counter}{ext}")
                    counter += 1

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(img_response.content)

                print(f"图片 {idx} 已保存至：{file_path}")

            except Exception as e:
                print(f"下载失败【{url}】错误信息：{str(e)}")
    else:
        print("无实拍图片")
def extract_id_bid(url):
    """
    从装装修网站URL中提取id和bid参数
    示例URL：https://www.zhuangxiaozhuang.com/index.php?s=/index/goods/index/id/221001/bid/1209668.html
    """
    # 修改后的正则表达式模式（允许更灵活的路径结构）
    pattern = r'/id/(\d+).*?/bid/(\d+)'
    match = re.search(pattern, url)

    if not match:
        raise ValueError("URL格式错误，未找到id/bid参数")

    return int(match.group(1)), int(match.group(2))
def read_excel_column(file_path, column_index=0):
    try:
        # 读取Excel文件（使用openpyxl引擎）
        df = pd.read_excel(file_path, engine='openpyxl')

        # 验证列索引有效性
        if column_index < 0 or column_index >= len(df.columns):
            raise ValueError(f"无效列索引，可用列范围：0-{len(df.columns) - 1}")

        # 转换为列表并去除空值
        column_data = df.iloc[:, column_index].dropna().tolist()
        return column_data

    except FileNotFoundError:
        raise FileNotFoundError(f"文件不存在：{file_path}")
    except Exception as e:
        raise RuntimeError(f"读取Excel失败：{str(e)}")



path_name = read_excel_column(r"F:\兼职\福满堂\福满堂上架表6.11.xlsx", 3)
urls = read_excel_column(r"F:\兼职\福满堂\福满堂上架表6.11.xlsx", 36)
save_root = r"F:\兼职\福满堂\实拍"
for i in range(len(urls)):
    try:
        save_path = os.path.join(save_root, path_name[i] + "实拍")
        id, bid = extract_id_bid(urls[i])
    except ValueError as e:
        print(f"URL格式错误：{urls[i]}，错误信息：{str(e)}")
    else:
        get_comment(id,save_path, path_name[i])
        print(i)
