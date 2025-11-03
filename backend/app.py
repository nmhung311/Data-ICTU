from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pdfplumber
import os
from datetime import datetime
import uuid
from database import init_db, save_document, get_document, get_all_documents, delete_document, update_document_metadata
# Import metadata generator
try:
    from gen_meta.document_splitter import split_vietnamese_legal_document
    GEN_META_AVAILABLE = True
    print("✅ Metadata generator đã sẵn sàng")
except ImportError as e:
    GEN_META_AVAILABLE = False
    print(f"⚠️ Metadata generator không khả dụng: {e}")

# OCR imports (optional - only if pytesseract is available)
# Thêm user site-packages vào path để tìm modules đã cài
import sys
import site
# Lấy user site-packages directory tự động
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import fitz  # PyMuPDF
    import io
    import re
    import unicodedata
    OCR_AVAILABLE = True
    print("✅ OCR (pytesseract) đã sẵn sàng")
except ImportError as e:
    OCR_AVAILABLE = False
    import io  # Vẫn cần io cho các phần khác
    import re
    import unicodedata
    print(f"⚠️ OCR không khả dụng: {e}")
    print("⚠️ Để cài đặt: pip3 install --break-system-packages pytesseract pillow PyMuPDF")
    print("⚠️ Và cài Tesseract engine: sudo apt install tesseract-ocr tesseract-ocr-vie")

# Import để xử lý file DOCX (optional)
try:
    from docx import Document
    DOCX_AVAILABLE = True
    print("✅ DOCX support đã sẵn sàng")
except ImportError as e:
    DOCX_AVAILABLE = False
    print(f"⚠️ DOCX support không khả dụng: {e}")
    print("⚠️ Để cài đặt: pip3 install --break-system-packages python-docx")

app = Flask(__name__)
CORS(app)  # Cho phép frontend gọi API

# Thư mục lưu file upload
# Vercel có read-only filesystem, cần dùng /tmp
# Detect Vercel: Kiểm tra VERCEL env var TRƯỚC (được set trong app.py/api/index.py)
# Nếu không có env var, kiểm tra __file__ path
try:
    _current_file = __file__
except NameError:
    _current_file = ''

IS_VERCEL = os.environ.get('VERCEL', '').lower() == '1' or '/var/task' in str(_current_file)

# Luôn dùng /tmp/uploads trên Vercel NGAY TỪ ĐẦU
# HOÀN TOÀN KHÔNG TẠO THƯ MỤC KHI IMPORT - chỉ tạo khi upload file
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
    print(f"🔍 Vercel detected - using /tmp/uploads (will create on first upload)")
else:
    UPLOAD_FOLDER = 'uploads'
    # Chỉ tạo thư mục trên local development - wrap trong try để tránh fail
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            print(f"✅ Created uploads folder: {UPLOAD_FOLDER}")
    except (OSError, PermissionError) as e:
        # Nếu không thể tạo, fallback về /tmp nếu có
        if os.path.exists('/tmp') and os.access('/tmp', os.W_OK):
            UPLOAD_FOLDER = '/tmp/uploads'
            print(f"⚠️ Cannot create uploads/, using fallback: {UPLOAD_FOLDER}")
        else:
            print(f"⚠️ Cannot create uploads folder: {e}")
            # Vẫn set UPLOAD_FOLDER để app không crash, sẽ fail khi upload

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Khởi tạo database khi start app
init_db()


def normalize_text(text):
    """Chuẩn hóa text để xử lý encoding và các ký tự đặc biệt"""
    if not text:
        return ""
    
    try:
        # Chuyển đổi sang unicode và normalize
        # NFC (Canonical Composition) để đảm bảo các ký tự tiếng Việt được chuẩn hóa
        text = unicodedata.normalize('NFC', text)
        
        # Loại bỏ các ký tự control không cần thiết nhưng giữ lại line breaks
        text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', text)
        
        # Chuẩn hóa khoảng trắng: thay nhiều khoảng trắng bằng một
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Chuẩn hóa line breaks: thay nhiều line breaks bằng hai
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    except Exception as e:
        print(f"⚠️ Lỗi khi normalize text: {e}")
        # Nếu có lỗi, thử decode lại
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            return str(text).strip()
        except:
            return str(text).strip()


def preprocess_image(img):
    """Tiền xử lý ảnh để cải thiện chất lượng OCR"""
    try:
        # Chuyển sang grayscale nếu là màu
        if img.mode != 'L':
            img = img.convert('L')
        
        # Tăng contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)  # Tăng contrast 2 lần
        
        # Tăng sharpness để text rõ hơn
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
        
        # Áp dụng filter để giảm noise
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        return img
    except Exception as e:
        print(f"⚠️ Lỗi khi preprocess image: {e}, sử dụng ảnh gốc")
        return img


def extract_text_with_ocr(pdf_path):
    """Trích xuất text từ PDF bằng OCR (dùng cho PDF scanned) - phiên bản cải thiện"""
    if not OCR_AVAILABLE:
        return None
    
    text_content = []
    try:
        # Kiểm tra xem Tesseract có sẵn sàng không
        try:
            pytesseract.get_tesseract_version()
        except Exception as te:
            error_msg = f"Tesseract OCR engine chưa được cài đặt. Vui lòng cài: sudo apt install tesseract-ocr tesseract-ocr-vie. Chi tiết: {str(te)}"
            print(f"❌ {error_msg}")
            return error_msg
        
        # Mở PDF bằng PyMuPDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"🔍 Đang OCR PDF: {pdf_path}, tổng số trang: {total_pages}")
        
        # Cấu hình OCR tối ưu cho tiếng Việt
        # PSM modes: 6 = Assume a single uniform block of text, 3 = Fully automatic page segmentation (default)
        # PSM 6 thường tốt hơn cho tài liệu đã được scan rõ ràng
        ocr_config = '--psm 6 --oem 3'
        
        for page_num in range(total_pages):
            page = doc[page_num]
            # Render trang thành image với độ phân giải cao hơn (3x thay vì 2x)
            # Độ phân giải cao hơn sẽ cải thiện chất lượng OCR đáng kể
            mat = fitz.Matrix(3, 3)  # Zoom 3x để có độ phân giải tốt hơn
            pix = page.get_pixmap(matrix=mat, alpha=False)  # alpha=False để giảm memory
            img_data = pix.tobytes("png")
            
            # Chuyển sang PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Tiền xử lý ảnh để cải thiện chất lượng OCR
            img = preprocess_image(img)
            
            # Thử OCR với các ngôn ngữ khác nhau, ưu tiên tiếng Việt
            text = None
            langs_to_try = [
                'vie+eng',  # Tiếng Việt + Tiếng Anh
                'vie',      # Chỉ tiếng Việt
                'eng',      # Chỉ tiếng Anh (fallback)
            ]
            
            for lang in langs_to_try:
                try:
                    text = pytesseract.image_to_string(
                        img, 
                        lang=lang,
                        config=ocr_config
                    )
                    if text and text.strip():
                        print(f"✅ OCR trang {page_num + 1} với ngôn ngữ '{lang}': {len(text)} ký tự")
                        break
                except Exception as lang_error:
                    print(f"⚠️ Không thể OCR với ngôn ngữ '{lang}': {lang_error}")
                    continue
            
            if not text:
                # Nếu tất cả ngôn ngữ đều fail, thử không chỉ định ngôn ngữ
                try:
                    text = pytesseract.image_to_string(img, config=ocr_config)
                except:
                    text = ""
            
            # Chuẩn hóa text để xử lý encoding
            if text:
                text = normalize_text(text)
            
            if text and text.strip():
                text_content.append(f"## Trang {page_num + 1}\n\n{text}\n\n")
            else:
                print(f"⚠️ OCR trang {page_num + 1}: không có text được nhận dạng")
        
        doc.close()
        result = "\n".join(text_content)
        
        # Đảm bảo result là string UTF-8 hợp lệ
        if result:
            result = normalize_text(result)
            print(f"✅ OCR hoàn thành: {len(result)} ký tự tổng cộng")
            return result
        else:
            print(f"⚠️ OCR không trích xuất được text nào")
            return None
            
    except Exception as e:
        error_msg = f"Lỗi OCR: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


def extract_text_from_pdf(pdf_path):
    """Trích xuất text từ PDF và chuyển sang markdown. Tự động fallback sang OCR nếu cần."""
    text_content = []
    pages_without_text = []
    
    # Bước 1: Thử extract text trực tiếp từ PDF
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"📄 Đang trích xuất PDF: {pdf_path}, tổng số trang: {total_pages}")
            
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    # Chuẩn hóa text để xử lý encoding
                    text = normalize_text(text)
                    # Format thành markdown
                    text_content.append(f"## Trang {page_num}\n\n{text}\n\n")
                else:
                    print(f"⚠️ Trang {page_num} không có text layer")
                    pages_without_text.append(page_num)
        
        result = "\n".join(text_content)
        
        # Nếu có một số trang không có text hoặc kết quả quá ít, thử OCR cho các trang đó
        # Hoặc nếu toàn bộ không có text, dùng OCR cho tất cả
        if not result or len(result.strip()) < 50:
            print("🔄 Không tìm thấy đủ text layer, đang thử OCR...")
            ocr_result = extract_text_with_ocr(pdf_path)
            if ocr_result and not ocr_result.startswith("Tesseract OCR") and not ocr_result.startswith("Lỗi OCR"):
                return ocr_result
            else:
                return "Không thể trích xuất text từ PDF. File có thể chứa hình ảnh cần OCR. Vui lòng cài đặt: pip install pytesseract pillow PyMuPDF và cài Tesseract OCR engine."
        
        # Nếu có một số trang thiếu text, có thể kết hợp với OCR cho các trang đó
        # Nhưng để đơn giản, chỉ cần trả về kết quả hiện tại nếu đã đủ
        if pages_without_text:
            print(f"⚠️ Có {len(pages_without_text)} trang không có text layer: {pages_without_text}")
            # Có thể cải thiện sau bằng cách OCR riêng các trang này và kết hợp
        
        # Chuẩn hóa toàn bộ result
        result = normalize_text(result)
        print(f"✅ Trích xuất thành công: {len(result)} ký tự")
        return result
        
    except Exception as e:
        error_msg = f"Lỗi khi đọc PDF: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Thử OCR như fallback cuối cùng
        if OCR_AVAILABLE:
            print("🔄 Thử OCR như fallback...")
            ocr_result = extract_text_with_ocr(pdf_path)
            if ocr_result and not ocr_result.startswith("Tesseract OCR") and not ocr_result.startswith("Lỗi OCR"):
                return ocr_result
        
        return error_msg


def extract_text_from_file(filepath, filename):
    """Trích xuất text từ file (PDF, TXT, DOCX, v.v.)"""
    file_ext = os.path.splitext(filename.lower())[1]
    
    # Xử lý PDF
    if file_ext == '.pdf':
        return extract_text_from_pdf(filepath)
    
    # Xử lý TXT và các file text
    elif file_ext in ['.txt', '.md', '.markdown']:
        try:
            # Thử với encoding UTF-8
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ Trích xuất text từ {file_ext}: {len(content)} ký tự")
            return content
        except UnicodeDecodeError:
            # Nếu không được, thử với encoding khác
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
                print(f"✅ Trích xuất text từ {file_ext} (latin-1): {len(content)} ký tự")
                return content
            except Exception as e:
                error_msg = f"Lỗi khi đọc file text: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg
        except Exception as e:
            error_msg = f"Lỗi khi đọc file text: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    # Xử lý DOCX
    elif file_ext == '.docx' or file_ext == '.doc':
        if not DOCX_AVAILABLE:
            return "File DOCX không được hỗ trợ. Vui lòng cài đặt: pip3 install --break-system-packages python-docx"
        try:
            doc = Document(filepath)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            content = "\n\n".join(paragraphs)
            print(f"✅ Trích xuất text từ DOCX: {len(content)} ký tự")
            return content if content else "File DOCX không có nội dung text"
        except Exception as e:
            error_msg = f"Lỗi khi đọc file DOCX: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    # Các file khác - thử đọc như text
    else:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ Trích xuất text từ {file_ext}: {len(content)} ký tự")
            return content
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
                print(f"✅ Trích xuất text từ {file_ext} (latin-1): {len(content)} ký tự")
                return content
            except Exception as e:
                return f"Không thể đọc file {file_ext}: {str(e)}. Vui lòng đảm bảo file là text hoặc PDF."
        except Exception as e:
            return f"Lỗi khi đọc file {file_ext}: {str(e)}"


@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """API endpoint để upload file (PDF, TXT, DOCX, v.v.) - tự động trích xuất và lưu vào DB"""
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file được upload'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Không có file được chọn'}), 400
    
    # Hỗ trợ nhiều loại file: PDF, TXT, DOCX, MD, v.v.
    allowed_extensions = ['.pdf', '.txt', '.docx', '.doc', '.md', '.markdown']
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        return jsonify({
            'error': f'Định dạng file không được hỗ trợ. Các định dạng được hỗ trợ: {", ".join(allowed_extensions)}'
        }), 400
    
    # Tạo document_id duy nhất
    document_id = str(uuid.uuid4())
    
    # Lưu file
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    upload_folder = app.config['UPLOAD_FOLDER']
    
    # Đảm bảo thư mục tồn tại trước khi save (trên Vercel sẽ dùng /tmp/uploads)
    try:
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
    except (OSError, PermissionError):
        pass  # Trên Vercel /tmp/uploads sẽ tự có
    
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    # Tự động trích xuất text (xử lý cả PDF và các file khác)
    print(f"🔄 Đang trích xuất text từ file: {filepath} (loại: {file_ext})")
    if file_ext == '.pdf':
        ocr_text = extract_text_from_pdf(filepath)
    else:
        # Nếu không phải PDF, dùng hàm extract_text_from_file
        ocr_text = extract_text_from_file(filepath, file.filename)
    
    # Đảm bảo ocr_text là string và được chuẩn hóa encoding
    if ocr_text:
        if not isinstance(ocr_text, str):
            ocr_text = str(ocr_text)
        ocr_text = normalize_text(ocr_text)
    
    # Lưu vào database (chưa có metadata)
    if save_document(document_id, file.filename, filepath, ocr_text):
        print(f"✅ Đã lưu document vào DB: {document_id}")
        
        # KHÔNG tự động tạo metadata - chỉ tạo khi người dùng yêu cầu qua API /api/generate-metadata
        # Metadata sẽ được tạo thủ công bằng cách gọi API endpoint riêng
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'filename': filename,
            'filepath': filepath,
            'message': 'Upload và trích xuất thành công',
            'metadata': None  # Không trả về metadata, người dùng phải tự tạo
        }), 200
    else:
        return jsonify({'error': 'Lỗi khi lưu vào database'}), 500


@app.route('/api/extract-pdf', methods=['POST'])
def extract_pdf():
    """API endpoint để trích xuất text từ PDF đã upload"""
    data = request.get_json()
    
    if 'filepath' not in data:
        return jsonify({'error': 'Thiếu filepath'}), 400
    
    filepath = data['filepath']
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File không tồn tại'}), 404
    
    # Trích xuất text sang markdown
    markdown_content = extract_text_from_pdf(filepath)
    
    return jsonify({
        'success': True,
        'markdown': markdown_content
    }), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint để xử lý câu hỏi và trả về markdown từ PDF"""
    data = request.get_json()
    
    if 'question' not in data or 'filepath' not in data:
        return jsonify({'error': 'Thiếu question hoặc filepath'}), 400
    
    question = data['question']
    filepath = data['filepath']
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File không tồn tại'}), 404
    
    # Trích xuất text từ PDF
    markdown_content = extract_text_from_pdf(filepath)
    
    # Kiểm tra nếu câu hỏi là yêu cầu trích xuất markdown
    question_lower = question.lower()
    is_extract_request = any(keyword in question_lower for keyword in ['trích xuất', 'extract', 'markdown', 'md'])
    
    # TODO: Ở đây có thể thêm logic xử lý câu hỏi với AI/LLM
    # Tạm thời trả về markdown content với thông tin câu hỏi
    
    if is_extract_request:
        # Nếu là yêu cầu trích xuất, trả về toàn bộ markdown
        answer = f"Đã nhận câu hỏi: '{question}'\n\nNội dung PDF đã được trích xuất sang Markdown:\n\n{markdown_content}"
    else:
        # Câu hỏi khác, trả về preview
        answer = f"Đã nhận câu hỏi: '{question}'\n\nNội dung PDF đã được trích xuất sang Markdown:\n\n{markdown_content[:500]}..."
    
    return jsonify({
        'success': True,
        'question': question,
        'markdown': markdown_content,
        'answer': answer
    }), 200


@app.route('/api/documents/<document_id>', methods=['GET'])
def get_document_api(document_id):
    """API endpoint để lấy document từ DB theo document_id"""
    document = get_document(document_id)
    
    if document:
        return jsonify({
            'success': True,
            'document': document
        }), 200
    else:
        return jsonify({'error': 'Document không tồn tại'}), 404


@app.route('/api/documents', methods=['GET'])
def get_all_documents_api():
    """API endpoint để lấy tất cả documents"""
    documents = get_all_documents()
    return jsonify({
        'success': True,
        'documents': documents
    }), 200


@app.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document_api(document_id):
    """API endpoint để xóa document khỏi DB"""
    success, message = delete_document(document_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 404


@app.route('/api/generate-metadata', methods=['POST'])
def generate_metadata():
    """API endpoint để tạo metadata từ OCR text trong database (đã được chỉnh sửa encoding)"""
    if not GEN_META_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Metadata generator không khả dụng'
        }), 500
    
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({'error': 'Thiếu document_id'}), 400
        
        # Lấy document từ database (OCR text đã được người dùng chỉnh sửa lỗi encoding)
        document = get_document(document_id)
        if not document:
            return jsonify({'error': 'Document không tồn tại'}), 404
        
        # Lấy OCR text từ database (đã được chỉnh sửa)
        ocr_text = document.get('ocr_text')
        if not ocr_text:
            return jsonify({'error': 'Document chưa có nội dung OCR trong database'}), 400
        
        # Lấy filename từ document để phân loại category
        filename = document.get('filename', '')
        
        # Lấy OpenAI API key từ environment variable (nếu có)
        api_key = os.getenv('OPENAI_API_KEY')
        
        # Tạo metadata từ OCR text trong database
        print(f"🔄 Đang tạo metadata cho document: {document_id} (file: {filename})")
        metadata_markdown = split_vietnamese_legal_document(
            text=ocr_text,
            api_key=api_key,
            filename=filename,
            use_llm=True  # Sử dụng LLM nếu có API key
        )
        
        # Lưu metadata vào database
        if metadata_markdown:
            update_document_metadata(document_id, metadata_markdown)
            print(f"✅ Đã tạo và lưu metadata thành công cho document: {document_id}")
        else:
            print(f"⚠️ Metadata rỗng cho document: {document_id}")
        
        return jsonify({
            'success': True,
            'metadata': metadata_markdown,
            'document_id': document_id
        }), 200
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo metadata: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Lỗi khi tạo metadata: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend đang chạy'}), 200


@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    """Serve uploaded files (txt, md, etc.) để frontend có thể preview"""
    try:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            filename,
            as_attachment=False
        )
    except Exception as e:
        print(f"❌ Lỗi khi serve file {filename}: {e}")
        return jsonify({'error': 'File không tồn tại'}), 404


if __name__ == '__main__':
    print("🚀 Flask API đang chạy tại http://localhost:5000")
    print("📄 API Endpoints:")
    print("   POST /api/upload-pdf - Upload PDF file")
    print("   POST /api/extract-pdf - Trích xuất text từ PDF")
    print("   POST /api/chat - Xử lý câu hỏi với PDF")
    print("   POST /api/generate-metadata - Tạo metadata từ document")
    print("   GET /api/health - Health check")
    app.run(debug=True, port=5000, host='0.0.0.0')


