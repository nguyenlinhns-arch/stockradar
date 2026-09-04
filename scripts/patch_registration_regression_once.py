from pathlib import Path

path = Path("engine/tests/test_email_subscription_funnel.py")
text = path.read_text(encoding="utf-8")
stale = '        self.assertIn("Có · bản cơ bản", register)\n'
replacement = (
    '        self.assertIn("Báo cáo email 09:00 hằng ngày", register)\n'
    '        self.assertIn("Có khi hệ thống gửi đủ điều kiện", register)\n'
    '        self.assertIn("Có khi tín hiệu đạt chuẩn", register)\n'
)
if stale in text:
    text = text.replace(stale, replacement, 1)
elif "Có khi hệ thống gửi đủ điều kiện" not in text:
    raise SystemExit("Neither stale nor updated registration assertion found")
path.write_text(text, encoding="utf-8")
