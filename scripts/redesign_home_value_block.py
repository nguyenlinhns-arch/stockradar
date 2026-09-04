#!/usr/bin/env python3
"""Replace the verbose legacy buyer block when it still exists.

The AI-first homepage no longer contains that legacy block, so production builds
must treat its absence as an intentional no-op rather than a deployment error.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NEW_BLOCK = '''<section class="home-decision-v2" aria-labelledby="home-decision-v2-title">
      <div class="container">
        <header class="home-decision-v2-head">
          <div>
            <span class="panel-label">STOCKRADAR TRẢ LỜI ĐIỀU GÌ?</span>
            <h2 id="home-decision-v2-title">Nhập mã. Nhận ngay việc cần làm.</h2>
            <p>Mỗi mã được tách thành hai tình huống rõ ràng: chưa có hàng và đang nắm giữ. Sau đó mới tới vùng hành động và mức rủi ro.</p>
          </div>
          <a class="button button-primary" href="kiem-tra-co-phieu/">Tra cứu cổ phiếu</a>
        </header>

        <div class="home-decision-v2-grid">
          <article class="home-decision-v2-card">
            <span class="home-decision-v2-kicker">CHƯA CÓ HÀNG</span>
            <strong>MUA hay CHỜ</strong>
            <p>Biết ngay mã đã đủ điều kiện để cân nhắc vào vị thế hay vẫn nên đứng ngoài.</p>
          </article>
          <article class="home-decision-v2-card">
            <span class="home-decision-v2-kicker">ĐANG NẮM GIỮ</span>
            <strong>GIỮ · TĂNG · GIẢM · BÁN</strong>
            <p>Quyết định quản trị vị thế được tách riêng, không phụ thuộc câu hỏi mua mới.</p>
          </article>
          <article class="home-decision-v2-card home-decision-v2-card-accent">
            <span class="home-decision-v2-kicker">MỐC HÀNH ĐỘNG</span>
            <strong>Vùng mua · Stop · Target</strong>
            <p>Đi thẳng vào vùng giá, mức vô hiệu và mục tiêu để kiểm soát rủi ro trước khi hành động.</p>
          </article>
        </div>

        <div class="home-decision-v2-proof" aria-label="Điểm kiểm chứng StockRadar">
          <span><b>4</b> khung đầu tư</span>
          <span><b>4</b> mốc rà soát/ngày</span>
          <span><b>100%</b> có dấu thời gian</span>
          <span><b>Không đủ điều kiện</b> → CHỜ</span>
        </div>
      </div>
    </section>'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    home = output / "index.html"
    if not home.is_file():
        raise RuntimeError(f"Homepage missing: {home}")

    source = home.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<section class="buyer-first-section"\s+aria-labelledby="buyer-home-title">.*?</section>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    source, count = pattern.subn(NEW_BLOCK, source, count=1)

    if count == 0:
        ai_first = "data-stockradar-ai-center" in source or "home-ai-center-v1.css" in source
        if ai_first:
            print("Homepage decision block v2: SKIP (AI-first homepage has no legacy buyer block)")
            return
        raise RuntimeError("Expected one legacy buyer block or an AI-first homepage, found neither")

    css_tag = '<link rel="stylesheet" href="assets/home-decision-v2.css?v=20260904-decision2">\n'
    if "home-decision-v2.css" not in source:
        source = source.replace("</head>", css_tag + "</head>", 1)

    home.write_text(source, encoding="utf-8")
    print("Homepage decision block v2: PASS")


if __name__ == "__main__":
    main()
