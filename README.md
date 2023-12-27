1.现在config.env中配置个人的百度文字识别token。配置方法见：https://ai.baidu.com/ai-doc/REFERENCE/Ck3dwjhhu
2.AK_check 和SK_check是发票验真的token，价格比通用票据识别的token贵，可以分开配置。
3.首先运行invoice_OCR.py，得到sum.xlsx文件。
4.然后运行invoice_verify.py,输入上面sum.xlsx文件的存放路径，可以得到验真结果，存放于checked.xlsx。
