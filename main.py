import requests
from flask import Flask, render_template, request, send_file, make_response, jsonify
import urllib.parse
import random
import string
import base64
from urllib.parse import urlparse
from zapv2 import ZAPv2
import time
import os

app = Flask(__name__)
APIkey = 'hr3ma4m73f1m0bhm9kssjhk6jq'
app.config['SECRET_KEY'] = 'hr3ma4m73f1m0bhm9kssjhk6jq'
scan_progress = {
    "spiderProgress": 0,
    "activeScanProgress": 0
}
context_id = 1
apikey = 'hr3ma4m73f1m0bhm9kssjhk6jq'
context_name = 'Default Context'


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_html', methods=['POST'])
def generate_html():
    url = request.form.get('url')
    file_name = generate_random_name() + '.html'
    generate_html_file(url, file_name)
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
    file_url = request.form.get('file_url')
    url = request.form.get('url')
    try:
        response = requests.get(file_url)
        if response.status_code == 200:
            result = 'URL hợp lệ để quét'   
        else:
            result = 'URL không hợp lệ để quét'
    except requests.exceptions.RequestException as e:
        result = 'Lỗi kết nối: '
    return render_template('download.html', result=result, file_url=file_url, url=url)

@app.route('/start_scan', methods=['POST'])
def start_scan():
    url = request.form['url']
    status = "Scanning"
    zap = ZAPv2(apikey=APIkey)
    zap.core.new_session()
    set_include_in_context()
    set_form_based_auth()
    set_logged_in_indicator()
    user_id_response = set_user_auth_config()
    start_spider(user_id_response, url)
    start_active(url)
    status = "Completed";
    return render_template('download.html', url=url, status = status)

def set_include_in_context():
    zap = ZAPv2(apikey=APIkey)
    include_url = 'http://localhost:1337/.*'
    zap.context.include_in_context(context_name, include_url)
    print('Configured include and exclude regex(s) in context')


def set_logged_in_indicator():
    zap = ZAPv2(apikey=APIkey)
    logged_in_regex = '\Q<font color="red">Welcome Bee</font>\E'
    zap.authentication.set_logged_in_indicator(context_id, logged_in_regex)
    print('Configured logged in indicator regex: ')


def set_form_based_auth():
    zap = ZAPv2(apikey=APIkey)
    login_url = 'http://localhost:1337/login.php'
    login_request_data = 'login={%username%}&password={%password%}&security_level=0&form=submit'
    form_based_config = 'loginUrl=' + urllib.parse.quote(login_url) + '&loginRequestData=' + urllib.parse.quote(login_request_data)
    zap.authentication.set_authentication_method(context_id, 'formBasedAuthentication', form_based_config)
    print('Configured form based authentication')


def set_user_auth_config():
    user = 'Test User'
    username = 'bee'
    password = 'bug'

    zap = ZAPv2(apikey=APIkey)
    user_id = zap.users.new_user(context_id, user)
    user_auth_config = 'username=' + urllib.parse.quote(username) + '&password=' + urllib.parse.quote(password)
    zap.users.set_authentication_credentials(context_id, user_id, user_auth_config)
    zap.users.set_user_enabled(context_id, user_id, 'true')
    zap.forcedUser.set_forced_user(context_id, user_id)
    zap.forcedUser.set_forced_user_mode_enabled('true')
    print('User Auth Configured')
    return user_id


@app.route('/progress')
def progress():
    global scan_progress
    return jsonify(scan_progress)

def start_spider(user_id, url):
    target = url
    zap = ZAPv2(apikey=APIkey)
    zap.spider.scan_as_user(context_id, user_id, target)
    scan_id = zap.spider.scan(target)
    spider_progress(scan_id,target)   
    
#Quá trình spider
def spider_progress(scan_id,target):
    zap = ZAPv2(apikey=APIkey)
    global scan_progress
    scan_status = zap.spider.status(scan_id) #số %
    scan_progress["spiderProgress"] = int(scan_status)
        
    if int(scan_status) < 100: #Chưa scan xong
        time.sleep(1)
        spider_progress(scan_id,target)

#Bắt đầu active scan
def start_active(url):
        target = url
        zap = ZAPv2(apikey=APIkey)
        scan_id = zap.ascan.scan(target)
        active_progress(scan_id,target) 


#Quá trình active scan
def active_progress(scan_id,target): #Quá trình active scan
        zap = ZAPv2(apikey=APIkey)
        global scan_progress
        scan_status = zap.ascan.status(scan_id)
        scan_progress["activeScanProgress"] = int(scan_status)
        
        if int(scan_status) < 100: #Chưa quét 100%
            time.sleep(1)  
            active_progress(scan_id,target)  
        else:                      
            result = []
            result.append('Active Scan completed')

#Tạo báo cáo
@app.route('/report')
def generate_report():
    # Tạo báo cáo HTML từ ZAP
    zap = ZAPv2(apikey=APIkey)
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
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    encoded_string = base64.b64encode(random_string.encode()).decode()
    file_name = encoded_string[:32]
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
