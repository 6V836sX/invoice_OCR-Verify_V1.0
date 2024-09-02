'''
https://cloud.baidu.com/doc/OCR/s/cklbnrnwe #百度官方文档

'''
import os.path
import logging
from datetime import datetime
import requests
from decouple import Config,RepositoryEnv
import pandas as pd
from pprint import pprint


def setup_logging(target_dir):
    # 获取当前日期和时间的时间戳
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 提取目标目录的名称
    dir_name = os.path.basename(target_dir)
    
    # 创建日志文件名
    log_filename = f"./verifyLog/{current_timestamp}_{dir_name}.log"
    
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


def get_access_token(AK, SK):
    host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=' + AK + '&client_secret=' + SK
    response = requests.get(host)
    #     if response:
    #         print(response.json())
    logging.info("获取访问令牌成功")
    return response.json().get('access_token')


def renew_keys():
    configuration = Config(repository = RepositoryEnv('config.env'))
    AK = configuration.get('AK_check')
    SK = configuration.get('SK_check')
    access_token = get_access_token(AK,SK)  # access_token 从上面模块中定义的函数实时提取
    logging.info(f"access_token更新成功：{access_token}")
    return access_token


# 写一个函数，按下列对应关系，将params1中的key进行转换。
'''

        增值税专用发票：special_vat_invoice
        增值税电子专用发票：elec_special_vat_invoice
        增值税普通发票：normal_invoice
        增值税普通发票（电子）：elec_normal_invoice
        增值税普通发票（卷式）：roll_normal_invoice
        通行费增值税电子普通发票：toll_elec_normal_invoice
        区块链电子发票（目前仅支持深圳地区）：blockchain_invoice
        全电发票（专用发票）：elec_invoice_special
        全电发票（普通发票）：elec_invoice_normal
        货运运输业增值税专用发票：special_freight_transport_invoice
        机动车销售发票：motor_vehicle_invoice
        二手车销售发票：used_vehicle_invoice
        '''


def convert_key(key):
    key_dict = {
        '增值税专用发票':'special_vat_invoice',
        '增值税电子专用发票':'elec_special_vat_invoice',

        '全电发票（专用发票）':'elec_invoice_special',
        '全电发票（普通发票）':'elec_invoice_normal',

        '增值税普通发票':'normal_invoice',
        '增值税普通发票（电子）':'elec_invoice_normal',
        '电子普通发票':'elec_normal_invoice',
        '电子发票(普通发票)':'elec_invoice_normal',  # 全电发票
        '通行费电子普票':'toll_elec_normal_invoice',

        '增值税普通发票（卷式）':'roll_normal_invoice',
        '区块链电子发票（目前仅支持深圳地区）':'blockchain_invoice',

        '货运运输业增值税专用发票':'special_freight_transport_invoice',
        '机动车销售发票':'motor_vehicle_invoice',
        '二手车销售发票':'used_vehicle_invoice'
    }
    return key_dict[key]


def convert_date_str(date_str) -> str:
    # 去掉字符串中的非数字字符，只保留数字
    digits = ''.join(filter(str.isdigit,date_str))

    # 使用字符串的zfill方法在左侧补足0，确保总长度为8位
    formatted_date = digits.zfill(8)
    return formatted_date


# 写一个函数，按下列规则转换total_amount 或 AmountInFiguers

def convert_total_amount(InvoiceType,total_amount,AmountInFiguers) -> str:
    '''
    ���值税专票、电子专票、区块链电子发票、机动车销售发票、货运专票填写不含税金额；
    二手车销售发票填写车价合计；
    全电发票（专用发票）、全电发票（普通发票）填写价税合计金额，其他类型发票可为空
    '''
    if InvoiceType in ['special_vat_invoice','elec_special_vat_invoice','blockchain_invoice','motor_vehicle_invoice',
                       'special_freight_transport_invoice']:
        return total_amount
    elif InvoiceType == 'used_vehicle_invoice':
        return AmountInFiguers
    elif InvoiceType in ['elec_invoice_special','elec_invoice_normal','elec_normal_invoice']:
        return AmountInFiguers
    else:
        return None


'''
OCR-增值税发票验真
'''


def fp_check(payload, access_token) -> str:
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice_verification"
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type':'application/x-www-form-urlencoded'}
    response = requests.post(request_url,data = payload,headers = headers)
    if response:
        verify_message = str(response.json().get('VerifyMessage'))
        logging.info(f"验真结果: {verify_message}")
    return verify_message


if __name__ == '__main__':
    rscfilepath = input('��输入sum.xlsx文件完整路径：')
    setup_logging(os.path.dirname(rscfilepath))
    
    access_token = renew_keys()
    logging.info("开始读取Excel文件")
    df = pd.read_excel(io=rscfilepath, sheet_name='Sheet1', dtype=str)
    df['check_result'] = [''] * df.shape[0]
    
    for index, row in df.iterrows():
        logging.info(f"处理第 {index+1} 行")
        # 将row转换为字典
        params = row.to_dict()
        logging.info(f"当前行数据: {params}")
        
        # 用params构造fp_check所需要的参数,全电发票参数不同。
        invoice_type = convert_key(params["InvoiceType"])
        logging.info(f"转换后的发票类型: {invoice_type}")
        
        if invoice_type in ['elec_invoice_special','elec_invoice_normal']:
            params1 = {
                "invoice_num":str(params["InvoiceNum"]),
                "invoice_date":convert_date_str(str(params["InvoiceDate"])),
                "invoice_type":convert_key(params["InvoiceType"]),
                "total_amount":str(convert_total_amount(convert_key(params["InvoiceType"]),params["TotalAmount"],
                                                        params["AmountInFiguers"]))
            }
            payload = f'invoice_code=&invoice_num={params1["invoice_num"]}&invoice_date={params1["invoice_date"]}&invoice_type={params1["invoice_type"]}&check_code=&total_amount={params1["total_amount"]}'
        else:
            params1 = {
                "invoice_code":str(params["InvoiceCode"]),
                "invoice_num":str(params["InvoiceNum"]),
                "invoice_date":convert_date_str(str(params["InvoiceDate"])),
                "invoice_type":convert_key(params["InvoiceType"]),
                "check_code":str(params["CheckCode"])[-6:],
                "total_amount":str(convert_total_amount(convert_key(params["InvoiceType"]),params["TotalAmount"],
                                                        params["AmountInFiguers"]))
            }
            payload = f'invoice_code={params1["invoice_code"]}&invoice_num={params1["invoice_num"]}&invoice_date={params1["invoice_date"]}&invoice_type={params1["invoice_type"]}&check_code={params1["check_code"]}&total_amount={params1["total_amount"]}'

        logging.info(f'开始验真：{payload}')
        # 将验真结果写入df
        df.loc[index,'check_result'] = fp_check(payload,access_token)
        # df.sort_values(by = index,ascending = False,inplace = True)
        check_result_path= os.path.join(os.path.dirname(rscfilepath) ,'_checked.xlsx')
        df.to_excel(excel_writer = check_result_path)
        logging.info(f'第 {index+1} 行验真结束')
        logging.info("所有处理完成")
