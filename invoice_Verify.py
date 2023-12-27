'''
https://cloud.baidu.com/doc/OCR/s/cklbnrnwe #百度官方文档

'''

import requests
from decouple import Config,RepositoryEnv
import pandas as pd
from pprint import pprint


def get_access_token(AK,SK):
    host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=' + AK + '&client_secret=' + SK
    response = requests.get(host)
    #     if response:
    #         print(response.json())
    return response.json().get('access_token')


def renew_keys():
    configuration = Config(repository = RepositoryEnv('config.env'))
    AK = configuration.get('AK_check')
    SK = configuration.get('SK_check')
    access_token = get_access_token(AK,SK)  # access_token 从上面模块中定义的函数实时提取
    print('access_token更新成功：' + access_token)
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
        '电子发票(普通发票)':'elec_invoice_normal',   #全电发票
        '通行费增值税电子普通发票':'toll_elec_normal_invoice',

        '增值税普通发票（卷式）':'roll_normal_invoice',
        '区块链电子发票（目前仅支持深圳地区）':'blockchain_invoice',

        '货运运输业增值税专用发票':'special_freight_transport_invoice',
        '机动车销售发票':'motor_vehicle_invoice',
        '二手车销售发票':'used_vehicle_invoice'
    }
    return key_dict[key]


def convert_date_str(date_str)->str:
# 去掉字符串中的非数字字符，只保留数字
    digits = ''.join(filter(str.isdigit,date_str))

    # 使用字符串的zfill方法在左侧补足0，确保总长度为8位
    formatted_date = digits.zfill(8)
    return formatted_date


# 写一个函数，按下列规则转换total_amount 或 AmountInFiguers

def convert_total_amount(InvoiceType,total_amount,AmountInFiguers)->str:
    '''
    增值税专票、电子专票、区块链电子发票、机动车销售发票、货运专票填写不含税金额；
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


def fp_check(payload,access_token)->str:
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice_verification"
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type':'application/x-www-form-urlencoded'}
    response = requests.post(request_url,data = payload,headers = headers)
    if response:
        # print(response.json())
        pprint(f"验真结果:{str(response.json().get('VerifyMessage'))}")
    return str(response.json().get('VerifyMessage'))



if __name__ == '__main__':
    access_token = renew_keys() # access_token 从上面模块中定义的函数实时提取,使用.env中的AK_check和SK_check
    # 读取本目录下sum.xlsx文件，从中获取fp_check所需要的参数
    rscfilepath =input('请输入rename后的文件完整路径：')
    df = pd.read_excel(input=rscfilepath,sheet_name = 'Sheet1',dtype = str)
    df['check_result'] = ['']*df.shape[0]
    for index,row in df.iterrows():
        # print('这是第{}行'.format(index))
        # 将row转换为字典
        params = row.to_dict()
        # 用params构造fp_check所需要的参数,全电发票参数不同。
        if convert_key(params["InvoiceType"]) in ['elec_invoice_special','elec_invoice_normal']:
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
                       "total_amount":str(convert_total_amount(convert_key(params["InvoiceType"]),params["TotalAmount"],params["AmountInFiguers"]))
                       }
            payload = f'invoice_code={params1["invoice_code"]}&invoice_num={params1["invoice_num"]}&invoice_date={params1["invoice_date"]}&invoice_type={params1["invoice_type"]}&check_code={params1["check_code"]}&total_amount={params1["total_amount"]}'


        print(f'开始验真：{payload}\n\n')
        #将验真结果写入df
        df.loc[index,'check_result']=fp_check(payload,access_token)
        df.setsort_values(by = index,ascending = False,inplace = True)
        df.to_excel(excel_writer = "checked.xlsx")
        print('验真结束：','\n\n','-+-+-' * 20)