"""Final artifact switch after legacy compatibility QA; new product has its own QA.
Never imports private Project URLs, transcripts, report bodies or credentials.
"""
from pathlib import Path
import re,sys,shutil
ROOT=Path(__file__).resolve().parents[1]

def activate(dest):
    dest=Path(dest)
    assets=dest/'assets';assets.mkdir(parents=True,exist_ok=True)
    for name in ['execution-config.js','chatgpt-workspace.js','chatgpt-workspace.css','project-channel.js','project-channel.css']:
        source=ROOT/'website/assets'/name
        if source.resolve()!=(assets/name).resolve():shutil.copyfile(source,assets/name)
    page=dest/'bao-cao-chatgpt/index.html';page.parent.mkdir(parents=True,exist_ok=True)
    if page.resolve()!=(ROOT/'website/bao-cao-chatgpt/index.html').resolve():shutil.copyfile(ROOT/'website/bao-cao-chatgpt/index.html',page)
    for path in dest.rglob('*.html'):
        text=path.read_text(encoding='utf-8')
        text=re.sub(r'<script\b[^>]*src=[\"\'][^\"\']*/?(?:ai-center|ai-assistant)\.js[^\"\']*[\"\'][^>]*>\s*</script>','',text,flags=re.I)
        if 'data-stockradar-ai-center' in text or 'data-stockradar-chatgpt-reports' in text:
            if 'assets/execution-config.js' not in text:text=text.replace('</head>','<script src="assets/execution-config.js?v=20260907-workspace"></script>\n</head>')
            if 'assets/chatgpt-workspace.js' not in text:text=text.replace('</head>','<script src="assets/chatgpt-workspace.js?v=20260907-workspace" defer></script>\n</head>')
            if 'assets/chatgpt-workspace.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="assets/chatgpt-workspace.css?v=20260907-workspace">\n</head>')
        if 'data-stockradar-ai-center' in text:
            if 'assets/project-channel.js' not in text:text=text.replace('</head>','<script src="assets/project-channel.js?v=20260907-channel" defer></script>\n</head>')
            if 'assets/project-channel.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="assets/project-channel.css?v=20260907-channel">\n</head>')
        replacements={
          'AI không giới hạn':'Báo cáo và email theo gói','AI KHÔNG GIỚI HẠN':'BÁO CÁO VÀ EMAIL THEO GÓI',
          'hỏi AI không giới hạn':'lưu báo cáo và nhận email theo gói',
          '3 câu/ngày':'Chuẩn bị câu hỏi ChatGPT','10 câu/ngày':'Lưu báo cáo theo tài khoản',
          '3 câu / ngày':'Chuẩn bị câu hỏi ChatGPT','10 câu / ngày':'Lưu báo cáo theo tài khoản',
          'Hỏi liên tục như một cuộc trao đổi phân tích. Lịch sử được lưu theo tài khoản; dữ liệu cổ phiếu được lấy từ StockRadar khi cần.':'Phân tích trong ChatGPT bằng tài khoản của bạn. StockRadar lưu dữ liệu, lịch sử cũ và báo cáo được chọn; không gọi thêm mô hình API từ khung này.',
        }
        for old,new in replacements.items():text=text.replace(old,new)
        path.write_text(text,encoding='utf-8')
    for name in ['index.html','ai/index.html','bao-cao-chatgpt/index.html']:
        t=(dest/name).read_text(encoding='utf-8')
        assert 'assets/chatgpt-workspace.js' in t,name
        assert not re.search(r'<script[^>]*src=[\"\'][^\"\']*ai-center\.js',t),name
    print('CHATGPT_WORKSPACE activated: no legacy inference widget, generic ChatGPT destination, private report reader and explicit Project channel.')
if __name__=='__main__':activate(sys.argv[1] if len(sys.argv)>1 else '.pages-site')
