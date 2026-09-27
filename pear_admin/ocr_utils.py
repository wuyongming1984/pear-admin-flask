"""
OCR工具类 - 百度OCR增值税发票识别
"""
import base64
import json
import os

# 尝试导入requests，如果失败则在使用时报错
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class BaiduOCR:
    """百度OCR增值税发票识别"""
    
    def __init__(self, api_key=None, secret_key=None):
        self.api_key = api_key or os.getenv('BAIDU_OCR_API_KEY')
        self.secret_key = secret_key or os.getenv('BAIDU_OCR_SECRET_KEY')
        self.access_token = None
    
    def get_access_token(self):
        """获取access_token"""
        if not REQUESTS_AVAILABLE:
            raise Exception("requests模块未安装，无法使用百度OCR")
        
        if not self.api_key or not self.secret_key:
            raise RuntimeError("未配置百度 OCR，请设置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")

        if self.access_token:
            return self.access_token
            
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        # 临时禁用代理
        proxies = {
            "http": None,
            "https": None,
        }
        
        # 重试3次
        for i in range(3):
            try:
                # 忽略SSL警告
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.post(url, params=params, timeout=10, verify=False, proxies=proxies)
                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result.get("access_token")
                    return self.access_token
                else:
                    print(f"尝试 {i+1}/3 获取access_token失败: {response.status_code}")
            except Exception as e:
                print(f"尝试 {i+1}/3 获取access_token异常: {str(e)}")
                if i == 2: # 最后一次
                    raise Exception(f"获取access_token异常: {str(e)}")
                import time
                time.sleep(1)
        
        raise Exception("获取access_token失败: 重试次数超限")
    
    def recognize_invoice(self, file_path=None, file_content=None):
        """
        识别增值税发票
        
        Args:
            file_path: 文件路径 (可选)
            file_content: 文件二进制内容 (可选，优先级高于file_path)
            
        Returns:
            dict: 识别结果
        """
        if not REQUESTS_AVAILABLE:
            raise Exception("requests模块未安装，无法使用百度OCR")
        
        if not self.access_token:
            self.get_access_token()
            

        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={self.access_token}"
        
        try:
            image_data = None
            file_ext = ''
            
            # 1. 获取文件内容
            if file_content:
                # 如果提供了内容，尝试从file_path获取扩展名(如果有)，否则默认jpg
                if file_path:
                    file_ext = file_path.lower().split('.')[-1]
                else:
                    # 尝试检测
                    if file_content.startswith(b'%PDF'):
                         file_ext = 'pdf'
                    else:
                         file_ext = 'jpg'
            elif file_path:
                # 兼容 HTTPS URL
                if file_path.startswith('http'):
                    response = requests.get(file_path, timeout=30)
                    if response.status_code == 200:
                        file_content = response.content
                        file_ext = file_path.split('?')[0].lower().split('.')[-1]
                    else:
                        raise Exception(f"无法下载文件: {response.status_code}")
                # 本地文件
                elif os.path.exists(file_path):
                     file_ext = file_path.lower().split('.')[-1]
                     with open(file_path, 'rb') as f:
                        file_content = f.read()
                else:
                     raise Exception(f"文件不存在: {file_path}")
            else:
                raise Exception("必须提供 file_path 或 file_content")

            # 2. 处理内容 (PDF转图片 或 直接编码)
            if file_ext == 'pdf':
                # PDF需要特殊处理 (传入bytes)
                image_data = self._convert_pdf_to_image(file_content=file_content)
            else:
                image_data = base64.b64encode(file_content).decode('utf-8')
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_data}
            
            # 临时禁用代理
            proxies = {
                "http": None,
                "https": None,
            }
            
            # 重试3次
            for i in range(3):
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    response = requests.post(url, headers=headers, data=data, timeout=30, verify=False, proxies=proxies)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 检查是否有错误
                        if 'error_code' in result:
                            error_msg = result.get('error_msg', '未知错误')
                            # 如果是access_token失效，强制刷新后重试
                            if result.get('error_code') in [110, 111] and i < 2:
                                self.access_token = None
                                self.get_access_token()
                                url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={self.access_token}"
                                continue
                                
                            raise Exception(f"OCR识别失败: {error_msg}")
                        
                        # 解析识别结果
                        if 'words_result' in result:
                            return self.parse_invoice_result(result['words_result'])
                        else:
                            raise Exception("OCR返回结果格式异常")
                    else:
                        if i == 2:
                            raise Exception(f"API请求失败: HTTP {response.status_code}")
                except Exception as e:
                    if i == 2:
                        raise e
                    import time
                    time.sleep(1)
                
        except Exception as e:
            raise Exception(f"OCR识别异常: {str(e)}")
    
    def _convert_pdf_to_image(self, pdf_path=None, file_content=None):
        """
        将PDF转换为图片（base64）
        优先使用pdf2image，如果不可用则使用PyMuPDF
        """
        try:
            # 尝试使用pdf2image
            from pdf2image import convert_from_path, convert_from_bytes
            import io
            
            print("使用pdf2image转换PDF...")
            images = None
            if file_content:
                images = convert_from_bytes(file_content, first_page=1, last_page=1, dpi=200)
            elif pdf_path:
                images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
            
            if images:
                # 将第一页转换为base64
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr.seek(0)
                return base64.b64encode(img_byte_arr.read()).decode('utf-8')
            else:
                raise Exception("PDF转换失败：无法提取页面")
                
        except ImportError:
            print("pdf2image不可用，尝试使用PyMuPDF...")
            try:
                import fitz  # PyMuPDF
                import io
                from PIL import Image
                
                # 打开PDF
                doc = None
                if file_content:
                     doc = fitz.open(stream=file_content, filetype="pdf")
                elif pdf_path:
                     doc = fitz.open(pdf_path)
                
                if not doc or len(doc) == 0:
                    raise Exception("PDF文件为空")
                
                # 获取第一页
                page = doc[0]
                
                # 转换为图片（提高分辨率以获得更好的OCR效果）
                mat = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 转换为base64
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr.seek(0)
                
                doc.close()
                return base64.b64encode(img_byte_arr.read()).decode('utf-8')
                
            except ImportError:
                raise Exception("PDF转换失败：需要安装 pdf2image 或 PyMuPDF (pip install pdf2image 或 pip install PyMuPDF)")
            except Exception as e:
                raise Exception(f"PDF转换失败: {str(e)}")
    
    def parse_invoice_result(self, words_result):
        """
        解析发票识别结果
        
        Args:
            words_result: 百度OCR返回的words_result字段
            
        Returns:
            dict: 解析后的字典
        """
        def get_word(key):
            # 兼容不同的返回格式
            val = words_result.get(key)
            if isinstance(val, dict):
                return val.get('word', '')
            elif isinstance(val, str):
                return val
            return ''
        
        # 解析明细
        details = []
        try:
            # 聚合所有明细行
            rows = {}
            detail_keys = {
                'CommodityName': 'name',
                'CommodityType': 'spec',
                'CommodityUnit': 'unit',
                'CommodityNum': 'quantity',
                'CommodityPrice': 'price',
                'CommodityAmount': 'amount',
                'CommodityTaxRate': 'tax_rate',
                'CommodityTax': 'tax'
            }
            
            for key, field_name in detail_keys.items():
                items = words_result.get(key, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            # Ensure row_id is string
                            row_id = str(item.get('row', '0'))
                            if row_id not in rows:
                                rows[row_id] = {}
                            rows[row_id][field_name] = item.get('word', '')
            
            # 按行号排序并生成列表
            # x[0] is guaranteed to be string now
            sorted_rows = sorted(rows.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
            
            for _, row_data in sorted_rows:
                # 至少要有名称或金额才算有效行
                if row_data.get('name') or row_data.get('amount'):
                    details.append(row_data)
            
            print(f"解析到 {len(details)} 条明细")
                    
        except Exception as e:
            print(f"明细解析失败: {str(e)}")
            import traceback
            traceback.print_exc()

        return {
            'invoice_number': get_word('InvoiceNum'),
            'invoice_code': get_word('InvoiceCode'),
            'invoice_date': get_word('InvoiceDate'),
            'invoice_type': get_word('InvoiceType'),
            'invoice_name': get_word('InvoiceTypeOrg'), # 发票名称
            'check_code': get_word('CheckCode'),
            'machine_code': get_word('MachineCode'),
            
            'buyer_name': get_word('PurchaserName'),
            'buyer_tax_num': get_word('PurchaserRegisterNum'),
            'buyer_address': get_word('PurchaserAddress'),
            'buyer_bank': get_word('PurchaserBank'),
            
            'seller_name': get_word('SellerName'),
            'seller_tax_num': get_word('SellerRegisterNum'),
            'seller_address': get_word('SellerAddress'),
            'seller_bank': get_word('SellerBank'),
            
            'total_amount': get_word('TotalAmount'),
            'total_tax': get_word('TotalTax'),
            'amount_in_words': get_word('AmountInWords'),
            'amount_in_figuers': get_word('AmountInFiguers'),
            
            'remarks': get_word('Remarks'),
            'payee': get_word('Payee'),
            'checker': get_word('Checker'),
            'note_drawer': get_word('NoteDrawer'),
            'province': get_word('Province'),
            'city': get_word('City'),
            'password': get_word('Password'),
            
            'details': details,
            'raw_result': words_result  # 保存原始结果
        }




def get_ocr_instance():
    """使用环境变量配置真实 OCR；缺少配置时在识别前明确报错。"""
    return BaiduOCR()
