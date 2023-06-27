import requests
from flask import Flask, render_template, request, send_file, make_response, jsonify
import random
import string
import base64
from urllib.parse import urlparse
from zapv2 import ZAPv2
import time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a44cr1eoi1jnsoleuspocs0mr7'
scan_progress = {
    "spiderProgress": 0,
    "activeScanProgress": 0
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_html', methods=['POST'])
def generate_html():
    url = request.form.get('url')
    file_name = generate_random_name() + '.html'
    generate_html_file(url, file_name)
    scan_progress["spiderProgress"] = 0
    scan_progress["activeScanProgress"] = 0
    domain = get_domain_from_url(url)
    print(domain)
    file_url = f'http://{domain}/{file_name}'
    return render_template('download.html', file_name=file_name, file_url=file_url, url=url, status = "HTML generated")

@app.route('/download/<file_name>')
def download(file_name):
    # Đường dẫn thư mục hiện tại (thư mục chứa file Python)
    current_dir = os.path.dirname(os.path.abspath(__file__))
  
    # Đường dẫn đầy đủ đến file HTML trong thư mục "static"
    file_path = os.path.join(current_dir, 'static', file_name)
  
    # Kiểm tra xem file tồn tại hay không
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return f"File {file_name} không tồn tại.";
    
@app.route('/verify', methods=['POST'])
def verify():
    # domain = get_domain_from_url(url)
    scan_progress["spiderProgress"] = 0
    scan_progress["activeScanProgress"] = 0
    file_url = request.form.get('file_url')
    url = request.form.get('url')
    print(url)
    print(file_url)
    try:
        response = requests.get(file_url)
        if response.status_code == 200:
            result = 'URL hợp lệ để quét'
            
        else:
            result = 'URL không hợp lệ để quét'
    except requests.exceptions.RequestException as e:
        result = 'Lỗi kết nối: ' + str(e)
    return render_template('download.html', result=result, file_url=file_url, url=url)

@app.route('/start_scan', methods=['POST'])
def start_scan():
    url = request.form['url']
    print(url)
    status = "Scanning"
    scan_progress["spiderProgress"] = 0
    scan_progress["activeScanProgress"] = 0
    start_spider(url)
    start_active(url)
    status = "Completed";
    return render_template('download.html', url=url, status = status)

@app.route('/progress')
def progress():
    global scan_progress
    return jsonify(scan_progress)

def start_spider(url): #spider
    target = url
    apiKey = 'a44cr1eoi1jnsoleuspocs0mr7'
    zap = ZAPv2(apikey=apiKey)
    zap.core.new_session()
    scan_id = zap.spider.scan(target)
    spider_progress(scan_id,target)  # Bắt đầu in quá trình quét    
    
def spider_progress(scan_id,target): #in ra quá trình Spider
    apiKey = 'a44cr1eoi1jnsoleuspocs0mr7'
    zap = ZAPv2(apikey=apiKey)
    global scan_progress
    scan_status = zap.spider.status(scan_id) #số %
    scan_progress["spiderProgress"] = int(scan_status)
        
    if int(scan_status) < 100: #Chưa scan xong
        time.sleep(1)
        spider_progress(scan_id,target)

def start_active(url):
        target = url
        apiKey = 'a44cr1eoi1jnsoleuspocs0mr7'
        zap = ZAPv2(apikey=apiKey)
        scan_id = zap.ascan.scan(target)
        active_progress(scan_id,target) 

def active_progress(scan_id,target): #Quá trình active scan
        apiKey = 'a44cr1eoi1jnsoleuspocs0mr7'
        zap = ZAPv2(apikey=apiKey)
        global scan_progress
        scan_status = zap.ascan.status(scan_id)
        scan_progress["activeScanProgress"] = int(scan_status)
        
        if int(scan_status) < 100: #Chưa quét 100%
            time.sleep(1)  
            active_progress(scan_id,target)  
        else:                      
            result = []
            result.append('Active Scan completed')
            # hosts = ', '.join(zap.core.hosts)
            # alerts = zap.core.alerts(baseurl=target)
            # self.socketio.emit('scan_result', {'result': result, 'hosts': hosts, 'alerts': alerts}, namespace='/scan')

@app.route('/report')
def generate_report():
    # Tạo báo cáo HTML từ ZAP
    apiKey = 'a44cr1eoi1jnsoleuspocs0mr7'
    zap = ZAPv2(apikey=apiKey)
    report_html = zap.core.htmlreport()
    
    # Đường dẫn thư mục hiện tại (thư mục chứa file Python)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Đường dẫn thư mục lưu trữ báo cáo
    report_dir = os.path.join(current_dir, 'report')

    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Đường dẫn đầy đủ đến file báo cáo
    report_path = os.path.join(report_dir, 'report.html')
    
    # Lưu báo cáo vào file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_html)
    
    # Lưu báo cáo vào một file tạm thời
    # temp_file_path = 'report.html'
    # with open(temp_file_path, 'w', encoding='utf-8') as f:
    #     f.write(report_html)
    
    # # Trả về file báo cáo để tải xuống
    # return send_file(temp_file_path, as_attachment=True)
    
    # Tạo response
    response = make_response(report_html)
    
    # Thiết lập header để mở trong tab mới
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'inline; filename=report.html'
    
    return response

def get_domain_from_url(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain

def generate_random_name():
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    encoded_string = base64.b64encode(random_string.encode()).decode()
    file_name = encoded_string[:8]
    return file_name

def generate_html_file(url, file_name):
    html_content = f'''
    <html>
    <head>
        <title>Generated HTML</title>
    </head>
    <body>
        <h1>Generated HTML</h1>
        <p>URL: {url}</p>
    </body>
    </html>
    '''
    # Đường dẫn thư mục hiện tại (thư mục chứa file Python)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Đường dẫn thư mục lưu trữ báo cáo
    report_dir = os.path.join(current_dir, 'static')

    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Đường dẫn đầy đủ đến file báo cáo
    report_path = os.path.join(report_dir, file_name)
        
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == '__main__':
    app.run(port=1338, debug = True)
