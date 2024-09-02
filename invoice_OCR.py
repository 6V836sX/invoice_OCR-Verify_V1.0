#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/12/27 22:15
# @Author  : summer
# @Site    :
# @File    : rename_fapiao.py
# @Software: PyCharm
'''
1.pdf转PIL
2.PIL 进百度API 识别，输出文件名
3.重命名pdf

'''
import base64
import glob
import os
import os.path
import re
import shutil
import tempfile
import pandas as pd
import requests
from PIL import Image
from decouple import Config,RepositoryEnv
from pdf2image import convert_from_path
from tqdm import tqdm
import logging
import os
from datetime import datetime

def setup_logging(target_dir):
    # 获取当前日期和时间的时间戳
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 提取目标目录的名称
    dir_name = os.path.basename(target_dir)
    
    # 创建日志文件名
    log_filename = f"./OCRLog/{current_timestamp}_{dir_name}.log"
    
    # 设置日志
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 获取根日志记录器并添加处理器
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"开始处理目录: {target_dir}")

def pdf2jpg(filename, outputDir):
    with tempfile.TemporaryDirectory() as path:
        images = convert_from_path(pdf_path=filename, dpi=200, output_folder=None, last_page=1,
                                   first_page=None,
                                   fmt='jpg')
        for index, img in enumerate(images):
            (path, filename) = os.path.split(filename)
            (file, ext) = os.path.splitext(filename)
            output_path = os.path.join(outputDir, file + '_page_%s.jpg' % (index))
            img.save(output_path)
    return output_path


def convertjpg(jpgfile,outdir,width=1920,height=1215):
    img=Image.open(jpgfile)
    try:
        new_img=img.resize((width,height),Image.BILINEAR)
        new_img.save(os.path.join(outdir,os.path.basename(jpgfile)))
    except Exception as e:
        print(e)
    return os.path.join(outdir,os.path.basename(jpgfile))

def get_access_token(AK, SK):
    host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=' + AK + '&client_secret=' + SK
    response = requests.get(host)
    #     if response:
    #         print(response.json())
    # print(type(response.json().get('access_token')))
    return response.json().get('access_token')



def renew_keys():
    configuration = Config(repository = RepositoryEnv('config.env'))
    AK = configuration.get('AK')
    SK = configuration.get('SK')
    access_token = get_access_token(AK, SK)  # access_token 从上面模块中定义的函数实时提取
    print('access_token更新成功：' + access_token)
    return access_token


def OCR_vat(jpgpath, access_token):
    f = open(jpgpath, 'rb')
    img = base64.b64encode(f.read())
    params = {"image": img}
    request_url_0 = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"  #电子发票识别url
    request_url = request_url_0 + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    j = requests.post(request_url, data=params, headers=headers)
    if j:
        return j.json().get('words_result')
    else:
        return (print('识别失败',jpgpath))

def parse_data(json_data):
    try:
        data={
            "InvoiceCode":json_data.get("InvoiceCode"),
            "InvoiceNum":json_data.get("InvoiceNum")
            }
        file_name = data.get("InvoiceCode") + '_' + data.get("InvoiceNum")
        return str(file_name)
    except Exception as e:
        print(e)
        return print(f'解析失败:{json_data}')

def rename_pdf(rsc,oldname,dst,filename):
    os.rename(rsc,os.path.join(dst,filename))
    # print('{}--->{}'.format(oldname, filename))
    return None


def parse_content(json_data):
    try:
        data={
            "InvoiceType":str(json_data.get("InvoiceType")),
            "InvoiceCode":str(json_data.get("InvoiceCode")),
            "InvoiceNum":str(json_data.get("InvoiceNum")),
            "InvoiceDate": str(json_data.get("InvoiceDate")),
            "CheckCode": str(json_data.get("CheckCode")),
            "PurchaserName": str(json_data.get("PurchaserName")),
            "PurchaserRegisterNum": json_data.get("PurchaserRegisterNum"),
            "SellerName": json_data.get("SellerName"),
            "SellerRegisterNum": json_data.get("SellerRegisterNum"),
            "TotalAmount": float('{:.2f}'.format(float(json_data.get("TotalAmount")))),#不含税金额
            "AmountInFiguers": float('{:.2f}'.format(float(json_data.get("AmountInFiguers")))),#价税合计
            "Remarks": json_data.get("Remarks")
            }
        return pd.DataFrame(data=data, index=[0])
    except Exception as e:
        logging.error(f'解析失败: {e}')
        logging.error(f'JSON数据: {json_data}')
        return pd.DataFrame()  # 如果解析失败，返回一个空的dataframe

#写一个函数，正则匹配获取InvoiceDate的月份，然后转换成数字
def get_month(InvoiceDate):
    try:
        month=re.findall(r'\d+',InvoiceDate)[1]
        return str(month)
    except Exception as e:
        print(e)
        return str(InvoiceDate)

def get_year(InvoiceDate):
    try:
        year=re.findall(r'\d+',InvoiceDate)[0]
        return str(year)
    except Exception as e:
        print(e)
        return str(InvoiceDate)


def main():
    targetdir: str = input('Enter the target dir:')  # 输入目标文件夹
    setup_logging(targetdir)
    
    # 遍历targetir目录下的所有pdf文件
    rscfiles = glob.glob(targetdir + '/**/*.[pP][dD][fF]',recursive = True)  # 获取目标文件夹下的所有pdf文件
    print(f'共有{len(rscfiles)}个pdf文件待处理')

    outdir = os.path.join("./") + "/temp"
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    access_token = renew_keys()
    df_sum = []
    for rscfile in tqdm(rscfiles, desc='Processing'):
        logging.info(f'正在处理文件: {rscfile}')
        print(rscfile)
        jpgfile = pdf2jpg(rscfile,outputDir = outdir)
        convertjpg(jpgfile = jpgfile,outdir = outdir)
        json_data = OCR_vat(jpgpath = jpgfile,access_token = access_token)
        df_sum.append(parse_content(json_data))

    # 统计所有发票信息
    result = pd.concat(df_sum).sort_values(['PurchaserRegisterNum', 'InvoiceDate'], ascending=[True, True])
    result.drop_duplicates(inplace=True)  # 去重
    result.index = pd.Index(range(1, len(result) + 1), name="序号")
    
    # 输出到Excel文件
    excel_path = os.path.join(targetdir, "sum.xlsx")
    result.to_excel(excel_writer=excel_path)
    
    logging.info(f'处理完成,共处理了{len(rscfiles)}个发票文件')
    logging.info(f'发票统计信息已保存到: {excel_path}')

    return None



if __name__ == "__main__":
    main()

