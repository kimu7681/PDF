import streamlit as st
import pypdf
import io
import zipfile
import math

# ==========================================
# ページ設定（iPadやスマホで見やすいように広めに設定）
# ==========================================
st.set_page_config(
    page_title="PDF 結合・分割 ツール",
    page_icon="📄",
    layout="centered"
)

# ==========================================
# ヘルパー関数群
# ==========================================
def parse_page_ranges(range_str, max_pages):
    """
    '1, 3-5' のような文字列を解釈し、0-indexedのページ番号リストを返す。
    空白の場合は全ページを返す。
    """
    if not range_str or not str(range_str).strip() or str(range_str).strip().lower() == "all":
        return list(range(max_pages))
    
    pages = set()
    for part in str(range_str).replace(" ", "").split(","):
        if not part: continue
        if "-" in part:
            parts = part.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start = max(1, int(parts[0]))
                end = min(max_pages, int(parts[1]))
                pages.update(range(start - 1, end))
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= max_pages:
                pages.add(p - 1)
    return sorted(list(pages))

def parse_split_ranges(range_str, max_pages):
    """
    '1-5, 6-10, 11' のような文字列を解釈し、分割グループごとのページ番号リストのリストを返す。
    """
    groups = []
    for part in str(range_str).replace(" ", "").split(","):
        if not part: continue
        pages = []
        if "-" in part:
            parts = part.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start = max(1, int(parts[0]))
                end = min(max_pages, int(parts[1]))
                if start <= end:
                    pages = list(range(start - 1, end))
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= max_pages:
                pages = [p - 1]
        
        if pages:
            groups.append(pages)
    return groups

# ==========================================
# メインUI構成
# ==========================================
def main():
    st.title("📄 PDF 結合・分割 ツール")
    st.markdown("PCでもiPadでも使いやすいように設計されています。データはサーバーに保存されず安全です。")

    # サイドバーでモード切り替え
    st.sidebar.title("メニュー")
    mode = st.sidebar.radio("機能を選択してください:", ["➕ PDFを結合する", "✂️ PDFを分割する"])
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **使い方**\n\niPadなどのタッチデバイスの場合、各入力欄やボタンは少し広めに作られています。タップして操作してください。")

    # ------------------------------------------
    # モードA: PDF結合
    # ------------------------------------------
    if mode == "➕ PDFを結合する":
        st.header("➕ PDF結合 (Merge)")
        st.write("複数のPDFファイルを1つにまとめます。ファイルごとの抽出ページ指定も可能です。")

        uploaded_files = st.file_uploader(
            "結合するPDFファイルをアップロード（複数選択可 / ドラッグ＆ドロップ対応）", 
            type="pdf", 
            accept_multiple_files=True
        )

        if uploaded_files:
            st.divider()
            st.subheader("📋 アップロードされたファイル一覧")
            st.info("ページ指定例: `空白`(全ページ)、`1`(1ページ目のみ)、`1-3`(1〜3ページ)、`1, 3-5`")

            file_page_settings = []

            # ファイルごとにページ指定UIを生成
            for i, file in enumerate(uploaded_files):
                file.seek(0)
                try:
                    reader = pypdf.PdfReader(file)
                    num_pages = len(reader.pages)
                except Exception:
                    st.error(f"ファイル '{file.name}' を読み込めませんでした。暗号化されているか破損している可能性があります。")
                    continue

                # タッチ操作を意識して、少し余白を持たせたカラム構成
                with st.container():
                    col1, col2 = st.columns([1.5, 1])
                    with col1:
                        st.write(f"**{i+1}. {file.name}**")
                        st.caption(f"全 {num_pages} ページ / 約 {file.size / 1024:.1f} KB")
                    with col2:
                        pages_input = st.text_input(
                            "抽出するページ", 
                            key=f"pages_merge_{i}", 
                            placeholder="例: 1, 3-5 (空欄で全ページ)",
                            label_visibility="collapsed"
                        )
                    st.markdown("<br>", unsafe_allow_html=True) # 少し余白をあける
                    
                file_page_settings.append((file, pages_input, num_pages))

            # 実行ボタン
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 結合してダウンロード", use_container_width=True, type="primary"):
                with st.spinner("結合処理中..."):
                    try:
                        merger = pypdf.PdfWriter()
                        for file, pages_input, max_pages in file_page_settings:
                            file.seek(0)
                            reader = pypdf.PdfReader(file)
                            target_pages = parse_page_ranges(pages_input, max_pages)
                            for p in target_pages:
                                merger.add_page(reader.pages[p])

                        # インメモリでPDFを生成
                        out_buffer = io.BytesIO()
                        merger.write(out_buffer)
                        
                        st.success("✅ 結合が完了しました！下のボタンからダウンロードしてください。")
                        st.download_button(
                            label="📥 結合されたPDFをダウンロード",
                            data=out_buffer.getvalue(),
                            file_name="merged_document.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    # ------------------------------------------
    # モードB: PDF分割
    # ------------------------------------------
    elif mode == "✂️ PDFを分割する":
        st.header("✂️ PDF分割 (Split)")
        st.write("1つのPDFファイルを複数のファイルに分割します。")

        uploaded_file = st.file_uploader(
            "分割するPDFファイルをアップロード", 
            type="pdf", 
            accept_multiple_files=False
        )

        if uploaded_file:
            uploaded_file.seek(0)
            try:
                reader = pypdf.PdfReader(uploaded_file)
                max_pages = len(reader.pages)
                file_size_mb = uploaded_file.size / (1024 * 1024)
            except Exception:
                st.error("ファイルを読み込めませんでした。暗号化されているか破損している可能性があります。")
                st.stop()

            st.success(f"**ファイル名:** {uploaded_file.name} (全 {max_pages} ページ, 約 {file_size_mb:.2f} MB)")
            
            # タッチデバイスでも押しやすいタブ UI
            tab1, tab2 = st.tabs(["📑 (a) ページ指定で分割", "💾 (b) 容量目安で分割"])

            # ---- (a) ページ指定分割 ----
            with tab1:
                st.write("指定したページ範囲ごとに別々のPDFファイルを作成します。")
                st.info("例: `1-5, 6-10, 11-15` と入力すると、3つのPDFファイルに分割されてZIP化されます。")
                
                split_input = st.text_input(
                    "分割範囲を指定してください", 
                    placeholder="例: 1-5, 6-10, 11"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 指定範囲で分割してダウンロード", use_container_width=True, type="primary"):
                    if split_input.strip():
                        with st.spinner("分割処理中..."):
                            try:
                                groups = parse_split_ranges(split_input, max_pages)
                                if not groups:
                                    st.warning("有効な範囲が指定されていません。")
                                else:
                                    # インメモリでZIPを生成
                                    zip_buffer = io.BytesIO()
                                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                                        for idx, group in enumerate(groups):
                                            writer = pypdf.PdfWriter()
                                            for p in group:
                                                writer.add_page(reader.pages[p])
                                            
                                            pdf_buffer = io.BytesIO()
                                            writer.write(pdf_buffer)
                                            # 元ファイル名から拡張子を抜いたものをプレフィックスにする
                                            base_name = uploaded_file.name.rsplit('.', 1)[0]
                                            zip_file.writestr(f"{base_name}_part{idx+1}.pdf", pdf_buffer.getvalue())
                                    
                                    st.success("✅ 分割が完了しました！ZIPファイルをダウンロードしてください。")
                                    st.download_button(
                                        label="📥 分割されたPDF(ZIP)をダウンロード",
                                        data=zip_buffer.getvalue(),
                                        file_name="split_pages.zip",
                                        mime="application/zip",
                                        use_container_width=True
                                    )
                            except Exception as e:
                                st.error(f"エラーが発生しました: {e}")
                    else:
                        st.warning("分割範囲を入力してください。")

            # ---- (b) 容量指定分割 ----
            with tab2:
                st.write("1ファイルあたりの最大容量（目安）を指定して、機械的に均等分割します。")
                
                target_mb = st.number_input(
                    "1ファイルあたりの最大容量 (MB)", 
                    min_value=0.1, 
                    value=2.0, 
                    step=0.5
                )
                
                # 容量のシミュレーション計算
                avg_mb_per_page = file_size_mb / max_pages if max_pages > 0 else 0
                
                if avg_mb_per_page > target_mb:
                    st.warning("⚠️ 1ページあたりの容量が指定された最大容量を超えています。1ページ単位で分割します。")
                    pages_per_file = 1
                elif avg_mb_per_page > 0:
                    pages_per_file = max(1, math.floor(target_mb / avg_mb_per_page))
                else:
                    pages_per_file = max_pages
                    
                num_files = math.ceil(max_pages / pages_per_file)
                
                st.info(
                    f"📊 **シミュレーション結果**\n\n"
                    f"現在の設定だと、1ファイルあたり最大 **{pages_per_file}ページ** となり、"
                    f"**約 {avg_mb_per_page * pages_per_file:.2f} MB** のファイルが **{num_files}個** 生成される予定です。\n\n"
                    f"*(※ページごとにデータ量が異なるため、あくまで目安となります)*"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 容量目安で分割してダウンロード", use_container_width=True, type="primary"):
                    with st.spinner("分割処理中..."):
                        try:
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                                for i in range(num_files):
                                    start_page = i * pages_per_file
                                    end_page = min((i + 1) * pages_per_file, max_pages)
                                    
                                    writer = pypdf.PdfWriter()
                                    for p in range(start_page, end_page):
                                        writer.add_page(reader.pages[p])
                                        
                                    pdf_buffer = io.BytesIO()
                                    writer.write(pdf_buffer)
                                    
                                    base_name = uploaded_file.name.rsplit('.', 1)[0]
                                    zip_file.writestr(f"{base_name}_size_part{i+1}.pdf", pdf_buffer.getvalue())
                                    
                            st.success("✅ 分割が完了しました！ZIPファイルをダウンロードしてください。")
                            st.download_button(
                                label="📥 分割されたPDF(ZIP)をダウンロード",
                                data=zip_buffer.getvalue(),
                                file_name="split_by_size.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
