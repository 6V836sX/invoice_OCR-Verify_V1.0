import logging
from flask import Flask, render_template, request, send_file, jsonify
from flask_socketio import SocketIO, emit
import os
import pandas as pd
from invoice_Verify import setup_logging, renew_keys, convert_key, convert_date_str, convert_total_amount, fp_check
from invoice_OCR import main as ocr_main

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置日志记录器
class SocketIOHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        socketio.emit('log', {'message': log_entry}, namespace='/')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/ocr', methods=['POST'])
def ocr():
    if 'directory' not in request.form:
        return jsonify({"error": "No directory provided"}), 400

    directory = request.form['directory']
    directory = os.path.abspath(directory)  # 转换为绝对路径
    if not os.path.isdir(directory):
        return jsonify({"error": "Invalid directory"}), 400

    try:
        result_path = ocr_main(directory, socketio)
        return send_file(result_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/verify', methods=['POST'])
def verify():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.xlsx'):
        filename = file.filename
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        setup_logging(os.path.dirname(file_path))
        access_token = renew_keys()

        df = pd.read_excel(file_path, sheet_name='Sheet1', dtype=str)
        df['check_result'] = [''] * df.shape[0]

        total_rows = df.shape[0]
        for index, row in df.iterrows():
            params = row.to_dict()
            invoice_type = convert_key(params["InvoiceType"])

            if invoice_type in ['elec_invoice_special', 'elec_invoice_normal']:
                params1 = {
                    "invoice_num": str(params["InvoiceNum"]),
                    "invoice_date": convert_date_str(str(params["InvoiceDate"])),
                    "invoice_type": convert_key(params["InvoiceType"]),
                    "total_amount": str(convert_total_amount(convert_key(params["InvoiceType"]), params["TotalAmount"], params["AmountInFiguers"]))
                }
                payload = f'invoice_code=&invoice_num={params1["invoice_num"]}&invoice_date={params1["invoice_date"]}&invoice_type={params1["invoice_type"]}&check_code=&total_amount={params1["total_amount"]}'
            else:
                params1 = {
                    "invoice_code": str(params["InvoiceCode"]),
                    "invoice_num": str(params["InvoiceNum"]),
                    "invoice_date": convert_date_str(str(params["InvoiceDate"])),
                    "invoice_type": convert_key(params["InvoiceType"]),
                    "check_code": str(params["CheckCode"])[-6:],
                    "total_amount": str(convert_total_amount(convert_key(params["InvoiceType"]), params["TotalAmount"], params["AmountInFiguers"]))
                }
                payload = f'invoice_code={params1["invoice_code"]}&invoice_num={params1["invoice_num"]}&invoice_date={params1["invoice_date"]}&invoice_type={params1["invoice_type"]}&check_code={params1["check_code"]}&total_amount={params1["total_amount"]}'

            df.loc[index, 'check_result'] = fp_check(payload, access_token)
            socketio.emit('progress', {'current': index + 1, 'total': total_rows}, namespace='/')
            socketio.sleep(0)  # 确保事件被发送

        result_path = os.path.join('results', f'{os.path.splitext(filename)[0]}_checked.xlsx')
        df.to_excel(result_path, index=False)

        return send_file(result_path, as_attachment=True)
    
    return jsonify({"error": "Invalid file format"}), 400

if __name__ == '__main__':
    # 配置日志记录器
    handler = SocketIOHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    socketio.run(app, debug=True, port=5001)  # 或者其他未被占用的端口号