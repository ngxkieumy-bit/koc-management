import streamlit as st
import sqlite3
import pandas as pd


# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect(
    "koc_data.db",
    check_same_thread=False
)

cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS koc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    phone TEXT,
    name TEXT,
    follower INTEGER DEFAULT 0,
    category TEXT,
    note TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT UNIQUE,
    commission REAL DEFAULT 0,
    target_gmv REAL DEFAULT 0,
    note TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT,
    report_month TEXT,
    creator_name TEXT,
    store_name TEXT,
    gmv REAL DEFAULT 0,
    ac REAL DEFAULT 0
)
""")

conn.commit()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="KOC Management & Analytics",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# FUNCTIONS
# =========================================================

def money(value):
    return f"{value:,.0f} đ"


def percent(value):
    return f"{value:.2f}%"


def clean_money(series):
    """
    Xử lý tiền TikTok dạng:
    17.683.683.391₫
    708.471.259₫
    0₫
    """

    return pd.to_numeric(
        series
        .astype(str)
        .str.replace("₫", "", regex=False)
        .str.replace("đ", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip(),
        errors="coerce"
    ).fillna(0)


def parse_tiktok_date(series):
    """
    File TikTok có dạng:

    2026-09-01-2026-09-30

    Lấy ngày đầu tiên:

    2026-09-01
    """

    text = (
        series
        .astype(str)
        .str.strip()
    )

    extracted = text.str.extract(
        r"(\d{4}-\d{2}-\d{2})",
        expand=False
    )

    return pd.to_datetime(
        extracted,
        format="%Y-%m-%d",
        errors="coerce"
    )


# =========================================================
# HEADER
# =========================================================

st.title(
    "📊 KOC Management & Analytics"
)

st.write(
    "Hệ thống quản lý KOC/KOL, Brand và phân tích dữ liệu TikTok"
)

st.divider()


# =========================================================
# MENU
# =========================================================

page = st.sidebar.radio(
    "MENU",
    [
        "🏠 Dashboard",
        "👤 KOC Database",
        "🏷️ Brand Database",
        "📊 Monthly Analytics"
    ]
)


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    total_koc = pd.read_sql(
        "SELECT COUNT(*) AS total FROM koc",
        conn
    ).iloc[0]["total"]

    total_brand = pd.read_sql(
        "SELECT COUNT(*) AS total FROM brands",
        conn
    ).iloc[0]["total"]

    total_month = pd.read_sql(
        """
        SELECT COUNT(DISTINCT report_month) AS total
        FROM analytics
        """,
        conn
    ).iloc[0]["total"]

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "👤 Tổng KOC",
            int(total_koc)
        )

    with col2:

        st.metric(
            "🏷️ Tổng Brand",
            int(total_brand)
        )

    with col3:

        st.metric(
            "📅 Tháng dữ liệu",
            int(total_month)
        )

    st.success(
        "🚀 Hệ thống KOC đang hoạt động."
    )

    data = pd.read_sql(
        """
        SELECT
            report_month,
            SUM(gmv) AS gmv,
            SUM(ac) AS ac
        FROM analytics
        GROUP BY report_month
        ORDER BY report_month DESC
        """,
        conn
    )

    if data.empty:

        st.info(
            "Chưa có dữ liệu Analytics."
        )

    else:

        data["Tỷ lệ hoa hồng"] = (
            data["ac"]
            / data["gmv"]
            * 100
        ).fillna(0)

        display = data.copy()

        display["gmv"] = (
            display["gmv"]
            .apply(money)
        )

        display["ac"] = (
            display["ac"]
            .apply(money)
        )

        display.columns = [
            "Tháng",
            "GMV",
            "Hoa hồng thực tế",
            "Tỷ lệ hoa hồng"
        ]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# KOC DATABASE
# =========================================================

elif page == "👤 KOC Database":

    st.header("👤 KOC Database")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "➕ Thêm KOC",
            "🔍 Kiểm tra KOC",
            "📥 Import Excel",
            "📋 KOC List"
        ]
    )


    # =====================================================
    # ADD KOC
    # =====================================================

    with tab1:

        st.subheader(
            "➕ Thêm KOC"
        )

        username = st.text_input(
            "TikTok Username",
            placeholder="@username"
        )

        phone = st.text_input(
            "Số điện thoại"
        )

        name = st.text_input(
            "Tên KOC"
        )

        follower = st.number_input(
            "Follower",
            min_value=0,
            step=1000
        )

        category = st.selectbox(
            "Ngành hàng",
            [
                "Beauty",
                "Fashion",
                "Food",
                "Lifestyle",
                "Mother & Baby",
                "Technology",
                "Other"
            ]
        )

        note = st.text_area(
            "Ghi chú"
        )

        if st.button(
            "💾 Lưu KOC",
            type="primary"
        ):

            username = username.strip()

            if not username:

                st.error(
                    "Vui lòng nhập username."
                )

            else:

                if not username.startswith("@"):
                    username = "@" + username

                try:

                    cursor.execute(
                        """
                        INSERT INTO koc
                        (
                            username,
                            phone,
                            name,
                            follower,
                            category,
                            note
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            username,
                            phone.strip(),
                            name.strip(),
                            int(follower),
                            category,
                            note.strip()
                        )
                    )

                    conn.commit()

                    st.success(
                        f"Đã lưu {username}!"
                    )

                except sqlite3.IntegrityError:

                    st.warning(
                        "KOC này đã tồn tại."
                    )


    # =====================================================
    # CHECK KOC
    # =====================================================

    with tab2:

        st.subheader(
            "🔍 Kiểm tra hàng loạt KOC"
        )

        usernames = st.text_area(
            "Paste username - mỗi dòng 1 username",
            height=180
        )

        if st.button(
            "🔎 Kiểm tra danh sách",
            type="primary"
        ):

            names = []

            for username in usernames.splitlines():

                username = username.strip()

                if username:

                    if not username.startswith("@"):
                        username = "@" + username

                    if username not in names:
                        names.append(username)

            if not names:

                st.warning(
                    "Vui lòng nhập username."
                )

            else:

                placeholders = ",".join(
                    ["?"] * len(names)
                )

                result = pd.read_sql(
                    f"""
                    SELECT
                        username,
                        phone,
                        name,
                        follower,
                        category
                    FROM koc
                    WHERE username IN ({placeholders})
                    """,
                    conn,
                    params=names
                )

                found = set(
                    result["username"]
                )

                output = []

                for username in names:

                    if username in found:

                        row = result[
                            result["username"]
                            == username
                        ].iloc[0]

                        output.append(
                            {
                                "Username": username,
                                "Trạng thái": "✅ ĐÃ CÓ",
                                "Số điện thoại": row["phone"],
                                "Tên": row["name"],
                                "Follower": row["follower"],
                                "Category": row["category"]
                            }
                        )

                    else:

                        output.append(
                            {
                                "Username": username,
                                "Trạng thái": "❌ CHƯA CÓ",
                                "Số điện thoại": "",
                                "Tên": "",
                                "Follower": "",
                                "Category": ""
                            }
                        )

                output_df = pd.DataFrame(
                    output
                )

                found_count = (
                    output_df["Trạng thái"]
                    == "✅ ĐÃ CÓ"
                ).sum()

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Tổng kiểm tra",
                    len(output_df)
                )

                col2.metric(
                    "✅ Đã có",
                    int(found_count)
                )

                col3.metric(
                    "❌ Chưa có",
                    len(output_df)
                    - int(found_count)
                )

                st.dataframe(
                    output_df,
                    use_container_width=True,
                    hide_index=True
                )


                phones = output_df[
                    output_df["Trạng thái"]
                    == "✅ ĐÃ CÓ"
                ]["Số điện thoại"]

                phone_text = "\n".join(
                    str(phone)
                    for phone in phones
                    if str(phone).strip()
                )

                if phone_text:

                    st.text_area(
                        "📱 Danh sách SĐT",
                        phone_text,
                        height=150
                    )


    # =====================================================
    # IMPORT KOC
    # =====================================================

    with tab3:

        st.subheader(
            "📥 Import KOC từ Excel"
        )

        st.write(
            "File cần có ít nhất:"
        )

        st.markdown(
            "**username** và **phone**"
        )

        uploaded_file = st.file_uploader(
            "Chọn file Excel",
            type=["xlsx", "xls"],
            key="koc_upload"
        )

        if uploaded_file:

            try:

                import_df = pd.read_excel(
                    uploaded_file
                )

                st.dataframe(
                    import_df.head(10),
                    use_container_width=True,
                    hide_index=True
                )

                if not {
                    "username",
                    "phone"
                }.issubset(import_df.columns):

                    st.error(
                        "Thiếu cột username hoặc phone."
                    )

                elif st.button(
                    "🚀 Import vào Database",
                    type="primary"
                ):

                    added = 0
                    updated = 0

                    for _, row in import_df.iterrows():

                        username = str(
                            row["username"]
                        ).strip()

                        if (
                            not username
                            or username == "nan"
                        ):
                            continue

                        if not username.startswith("@"):
                            username = "@" + username

                        phone = str(
                            row["phone"]
                        ).strip()

                        if phone == "nan":
                            phone = ""

                        name_value = str(
                            row.get(
                                "name",
                                ""
                            )
                        )

                        if name_value == "nan":
                            name_value = ""

                        follower_value = row.get(
                            "follower",
                            0
                        )

                        if pd.isna(
                            follower_value
                        ):
                            follower_value = 0

                        category_value = str(
                            row.get(
                                "category",
                                "Other"
                            )
                        )

                        if category_value == "nan":
                            category_value = "Other"

                        note_value = str(
                            row.get(
                                "note",
                                ""
                            )
                        )

                        if note_value == "nan":
                            note_value = ""

                        exists = cursor.execute(
                            """
                            SELECT id
                            FROM koc
                            WHERE username = ?
                            """,
                            (username,)
                        ).fetchone()

                        if exists:

                            cursor.execute(
                                """
                                UPDATE koc
                                SET
                                    phone = ?,
                                    name = ?,
                                    follower = ?,
                                    category = ?,
                                    note = ?
                                WHERE username = ?
                                """,
                                (
                                    phone,
                                    name_value,
                                    int(follower_value),
                                    category_value,
                                    note_value,
                                    username
                                )
                            )

                            updated += 1

                        else:

                            cursor.execute(
                                """
                                INSERT INTO koc
                                (
                                    username,
                                    phone,
                                    name,
                                    follower,
                                    category,
                                    note
                                )
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    username,
                                    phone,
                                    name_value,
                                    int(follower_value),
                                    category_value,
                                    note_value
                                )
                            )

                            added += 1

                    conn.commit()

                    st.success(
                        f"Import thành công! "
                        f"➕ {added} mới | "
                        f"🔄 {updated} cập nhật"
                    )

            except Exception as e:

                st.error(
                    f"Lỗi: {e}"
                )


    # =====================================================
    # KOC LIST
    # =====================================================

    with tab4:

        st.subheader(
            "📋 Danh sách KOC"
        )

        all_koc = pd.read_sql(
            """
            SELECT
                username,
                phone,
                name,
                follower,
                category,
                note
            FROM koc
            ORDER BY id DESC
            """,
            conn
        )

        search = st.text_input(
            "🔎 Tìm KOC",
            placeholder="Username / tên / SĐT"
        )

        if search.strip():

            q = search.lower().strip()

            all_koc = all_koc[
                all_koc["username"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
                |
                all_koc["name"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
                |
                all_koc["phone"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
            ]

        st.metric(
            "👤 Tổng KOC",
            len(all_koc)
        )

        st.dataframe(
            all_koc,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# BRAND DATABASE
# =========================================================

elif page == "🏷️ Brand Database":

    st.header(
        "🏷️ Brand Database"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Thêm Brand",
            "📥 Import Excel",
            "📋 Brand List"
        ]
    )


    # =====================================================
    # ADD BRAND
    # =====================================================

    with tab1:

        st.subheader(
            "➕ Thêm Brand"
        )

        brand_name = st.text_input(
            "Tên Brand",
            placeholder="Maison Lena"
        )

        commission = st.number_input(
            "Commission (%)",
            min_value=0.0,
            max_value=100.0,
            value=2.0,
            step=0.1
        )

        target_gmv = st.number_input(
            "🎯 GMV mục tiêu",
            min_value=0.0,
            value=0.0,
            step=1000000.0
        )

        note = st.text_area(
            "Ghi chú"
        )

        if st.button(
            "💾 Lưu Brand",
            type="primary"
        ):

            if not brand_name.strip():

                st.error(
                    "Vui lòng nhập tên Brand."
                )

            else:

                try:

                    cursor.execute(
                        """
                        INSERT INTO brands
                        (
                            brand_name,
                            commission,
                            target_gmv,
                            note
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            brand_name.strip(),
                            commission,
                            target_gmv,
                            note.strip()
                        )
                    )

                    conn.commit()

                    st.success(
                        "Đã lưu Brand!"
                    )

                except sqlite3.IntegrityError:

                    st.warning(
                        "Brand đã tồn tại."
                    )


    # =====================================================
    # IMPORT BRAND
    # =====================================================

    with tab2:

        st.subheader(
            "📥 Import Brand"
        )

        uploaded_brand = st.file_uploader(
            "Chọn file Excel",
            type=["xlsx", "xls"],
            key="brand_upload"
        )

        if uploaded_brand:

            brand_df = pd.read_excel(
                uploaded_brand
            )

            st.dataframe(
                brand_df.head(10),
                use_container_width=True,
                hide_index=True
            )

            required = {
                "brand_name",
                "commission",
                "target_gmv"
            }

            if not required.issubset(
                brand_df.columns
            ):

                st.error(
                    "File cần có: "
                    "brand_name, commission, target_gmv"
                )

            elif st.button(
                "🚀 Import Brand",
                type="primary"
            ):

                for _, row in brand_df.iterrows():

                    name = str(
                        row["brand_name"]
                    ).strip()

                    if not name:
                        continue

                    commission_value = row[
                        "commission"
                    ]

                    target_value = row[
                        "target_gmv"
                    ]

                    if pd.isna(
                        commission_value
                    ):
                        commission_value = 0

                    if pd.isna(
                        target_value
                    ):
                        target_value = 0

                    note_value = str(
                        row.get(
                            "note",
                            ""
                        )
                    )

                    cursor.execute(
                        """
                        INSERT INTO brands
                        (
                            brand_name,
                            commission,
                            target_gmv,
                            note
                        )
                        VALUES (?, ?, ?, ?)

                        ON CONFLICT(brand_name)
                        DO UPDATE SET
                            commission =
                                excluded.commission,
                            target_gmv =
                                excluded.target_gmv,
                            note =
                                excluded.note
                        """,
                        (
                            name,
                            float(
                                commission_value
                            ),
                            float(
                                target_value
                            ),
                            note_value
                        )
                    )

                conn.commit()

                st.success(
                    "Import Brand thành công!"
                )


    # =====================================================
    # BRAND LIST
    # =====================================================

    with tab3:

        st.subheader(
            "📋 Danh sách Brand"
        )

        brand_df = pd.read_sql(
            """
            SELECT
                brand_name,
                commission,
                target_gmv,
                note
            FROM brands
            ORDER BY id DESC
            """,
            conn
        )

        search_brand = st.text_input(
            "🔎 Tìm Brand"
        )

        if search_brand.strip():

            brand_df = brand_df[
                brand_df["brand_name"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_brand.lower(),
                    na=False
                )
            ]

        brand_df["TAP dự kiến nhận"] = (
            brand_df["target_gmv"]
            * brand_df["commission"]
            / 100
        )

        display = brand_df.copy()

        display["GMV mục tiêu"] = (
            display["target_gmv"]
            .apply(money)
        )

        display["TAP dự kiến nhận"] = (
            display["TAP dự kiến nhận"]
            .apply(money)
        )

        display = display[
            [
                "brand_name",
                "commission",
                "GMV mục tiêu",
                "TAP dự kiến nhận",
                "note"
            ]
        ]

        display.columns = [
            "Brand",
            "Commission (%)",
            "GMV mục tiêu",
            "TAP dự kiến nhận",
            "Ghi chú"
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "🏷️ Tổng Brand",
            len(brand_df)
        )

        col2.metric(
            "🔎 Kết quả",
            len(display)
        )

        col3.metric(
            "🎯 Tổng GMV mục tiêu",
            money(
                brand_df["target_gmv"].sum()
            )
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# MONTHLY ANALYTICS
# =========================================================

elif page == "📊 Monthly Analytics":

    st.header(
        "📊 Monthly Analytics"
    )

    st.write(
        "Upload báo cáo TikTok để tự động cập nhật GMV và hoa hồng TAP."
    )

    st.info(
        "📌 Hệ thống lấy: "
        "A = Ngày | F = KOC/NST | "
        "L = Brand | M = GMV | "
        "AC = Hoa hồng thực tế"
    )

    st.divider()

    st.subheader(
        "📥 Upload báo cáo TikTok"
    )

    uploaded_file = st.file_uploader(
        "Chọn file Custom Report TikTok",
        type=["xlsx", "xls"],
        key="analytics_upload"
    )


    # =====================================================
    # READ FILE
    # =====================================================

    if uploaded_file:

        try:

            # -------------------------------------------------
            # QUAN TRỌNG:
            # ĐỌC THEO VỊ TRÍ CỘT
            #
            # A = 0
            # F = 5
            # L = 11
            # M = 12
            # AC = 28
            # -------------------------------------------------

            raw = pd.read_excel(
                uploaded_file,
                usecols=[0, 5, 11, 12, 28]
            )


            st.success(
                f"Đã đọc {len(raw):,} dòng dữ liệu."
            )


            # -------------------------------------------------
            # ĐỔI TÊN
            # -------------------------------------------------

            raw.columns = [
                "report_date",
                "creator_name",
                "store_name",
                "gmv",
                "ac"
            ]


            # -------------------------------------------------
            # BỎ DÒNG TÓM TẮT
            # -------------------------------------------------

            raw = raw[
                raw["report_date"]
                .astype(str)
                .str.strip()
                .str.lower()
                != "tóm tắt"
            ].copy()


            # -------------------------------------------------
            # NGÀY
            #
            # Ví dụ:
            # 2026-09-01-2026-09-30
            #
            # => 2026-09-01
            # -------------------------------------------------

            raw["report_date"] = (
                parse_tiktok_date(
                    raw["report_date"]
                )
            )


            # -------------------------------------------------
            # KOC
            # -------------------------------------------------

            raw["creator_name"] = (
                raw["creator_name"]
                .fillna("")
                .astype(str)
                .str.strip()
            )


            # -------------------------------------------------
            # BRAND
            #
            # Trong file có thể có \r
            # -------------------------------------------------

            raw["store_name"] = (
                raw["store_name"]
                .fillna("")
                .astype(str)
                .str.replace(
                    "\r",
                    "",
                    regex=False
                )
                .str.strip()
            )


            # -------------------------------------------------
            # GMV = M
            # -------------------------------------------------

            raw["gmv"] = clean_money(
                raw["gmv"]
            )


            # -------------------------------------------------
            # AC = AC
            #
            # ĐÂY LÀ CỘT MÌNH DÙNG
            # -------------------------------------------------

            raw["ac"] = clean_money(
                raw["ac"]
            )


            # -------------------------------------------------
            # CHỈ GIỮ DÒNG CÓ NGÀY
            # -------------------------------------------------

            raw = raw[
                raw["report_date"].notna()
            ].copy()


            if raw.empty:

                st.error(
                    "Không đọc được ngày từ cột A."
                )

            else:

                # -------------------------------------------------
                # THÁNG
                # -------------------------------------------------

                raw["report_month"] = (
                    raw["report_date"]
                    .dt.strftime("%Y-%m")
                )


                st.success(
                    f"✅ Đã xử lý "
                    f"{len(raw):,} dòng hợp lệ."
                )


                # =================================================
                # PREVIEW
                # =================================================

                st.subheader(
                    "👀 Preview dữ liệu"
                )

                preview = raw[
                    [
                        "report_date",
                        "report_month",
                        "creator_name",
                        "store_name",
                        "gmv",
                        "ac"
                    ]
                ].head(10).copy()


                preview["report_date"] = (
                    preview["report_date"]
                    .dt.strftime("%d/%m/%Y")
                )


                preview["gmv"] = (
                    preview["gmv"]
                    .apply(money)
                )


                preview["ac"] = (
                    preview["ac"]
                    .apply(money)
                )


                preview.columns = [
                    "Ngày",
                    "Tháng",
                    "KOC/NST",
                    "Brand",
                    "GMV",
                    "Hoa hồng thực tế"
                ]


                st.dataframe(
                    preview,
                    use_container_width=True,
                    hide_index=True
                )


                # =================================================
                # FILE SUMMARY
                # =================================================

                total_gmv = raw["gmv"].sum()

                total_ac = raw["ac"].sum()

                ac_rate = (
                    total_ac
                    / total_gmv
                    * 100
                    if total_gmv != 0
                    else 0
                )


                col1, col2, col3 = st.columns(3)


                with col1:

                    st.metric(
                        "💰 Tổng GMV",
                        money(total_gmv)
                    )


                with col2:

                    st.metric(
                        "💵 Tổng hoa hồng thực tế",
                        money(total_ac)
                    )


                with col3:

                    st.metric(
                        "📊 Tỷ lệ hoa hồng",
                        percent(ac_rate)
                    )


                # =================================================
                # MONTHS
                # =================================================

                months_found = sorted(
                    raw["report_month"]
                    .unique()
                )


                st.write(
                    "📅 Tháng phát hiện:",
                    ", ".join(months_found)
                )


                st.divider()


                # =================================================
                # IMPORT
                # =================================================

                st.warning(
                    "Nếu tháng đã tồn tại, dữ liệu tháng đó "
                    "sẽ được thay thế để tránh trùng."
                )


                if st.button(
                    "🚀 Import dữ liệu Analytics",
                    type="primary"
                ):

                    # -------------------------------------------------
                    # XÓA DỮ LIỆU CŨ CỦA THÁNG
                    # -------------------------------------------------

                    for month in months_found:

                        cursor.execute(
                            """
                            DELETE FROM analytics
                            WHERE report_month = ?
                            """,
                            (month,)
                        )


                    # -------------------------------------------------
                    # INSERT DATA
                    # -------------------------------------------------

                    insert_rows = []

                    for row in raw.itertuples(
                        index=False
                    ):

                        insert_rows.append(
                            (
                                row.report_date.strftime(
                                    "%Y-%m-%d"
                                ),
                                row.report_month,
                                row.creator_name,
                                row.store_name,
                                float(row.gmv),
                                float(row.ac)
                            )
                        )


                    cursor.executemany(
                        """
                        INSERT INTO analytics
                        (
                            report_date,
                            report_month,
                            creator_name,
                            store_name,
                            gmv,
                            ac
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        insert_rows
                    )


                    conn.commit()


                    st.success(
                        f"🎉 Import thành công "
                        f"{len(insert_rows):,} dòng!"
                    )


                    st.rerun()

        except Exception as e:
            st.error(f"❌ Không thể đọc file TikTok: {e}")


    # =====================================================
    # DASHBOARD DATA
    # =====================================================

    analytics_data = pd.read_sql(
        """
        SELECT *
        FROM analytics
        """,
        conn
    )


    if analytics_data.empty:

        st.warning(
            "Chưa có dữ liệu Analytics. "
            "Hãy upload file TikTok ở trên."
        )

    else:

        st.divider()

        st.subheader(
            "📊 Dashboard"
        )


        # =================================================
        # FILTER MONTH
        # =================================================

        months = sorted(
            analytics_data[
                "report_month"
            ].dropna().unique(),
            reverse=True
        )


        col1, col2 = st.columns(2)


        with col1:

            selected_month = st.selectbox(
                "📅 Chọn tháng",
                months
            )


        month_data = analytics_data[
            analytics_data["report_month"]
            == selected_month
        ].copy()


        # =================================================
        # FILTER BRAND
        # =================================================

        brands = [
            "Tất cả"
        ] + sorted(
            month_data[
                "store_name"
            ]
            .dropna()
            .unique()
            .tolist()
        )


        with col2:

            selected_brand = st.selectbox(
                "🏷️ Chọn Brand",
                brands
            )


        if selected_brand != "Tất cả":

            month_data = month_data[
                month_data["store_name"]
                == selected_brand
            ]


        # =================================================
        # KPI
        # =================================================

        total_gmv = (
            month_data["gmv"]
            .sum()
        )


        total_ac = (
            month_data["ac"]
            .sum()
        )


        ac_rate = (
            total_ac
            / total_gmv
            * 100
            if total_gmv
            else 0
        )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "💰 Tổng GMV",
                money(total_gmv)
            )


        with col2:

            st.metric(
                "💵 Tổng hoa hồng thực tế",
                money(total_ac)
            )


        with col3:

            st.metric(
                "📊 Tỷ lệ hoa hồng",
                percent(ac_rate)
            )


        st.divider()


        # =================================================
        # TOP BRAND
        # =================================================

        st.subheader(
            "🏆 Top Brand"
        )


        top_brand = (
            month_data
            .groupby(
                "store_name",
                as_index=False
            )
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum")
            )
            .sort_values(
                "Hoa hồng thực tế",
                ascending=False
            )
            .head(20)
        )


        top_brand["Tỷ lệ hoa hồng"] = (
            top_brand["Hoa hồng thực tế"]
            / top_brand["GMV"]
            * 100
        ).fillna(0)


        brand_display = top_brand.copy()


        brand_display["GMV"] = (
            brand_display["GMV"]
            .apply(money)
        )


        brand_display["Hoa hồng thực tế"] = (
            brand_display["Hoa hồng thực tế"]
            .apply(money)
        )


        st.dataframe(
            brand_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # TOP KOC
        # =================================================

        st.subheader(
            "👑 Top KOC/NST"
        )


        top_koc = (
            month_data
            .groupby(
                "creator_name",
                as_index=False
            )
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum")
            )
            .sort_values(
                "Hoa hồng thực tế",
                ascending=False
            )
            .head(20)
        )


        top_koc["Tỷ lệ hoa hồng"] = (
            top_koc["Hoa hồng thực tế"]
            / top_koc["GMV"]
            * 100
        ).fillna(0)


        koc_display = top_koc.copy()


        koc_display["GMV"] = (
            koc_display["GMV"]
            .apply(money)
        )


        koc_display["Hoa hồng thực tế"] = (
            koc_display["Hoa hồng thực tế"]
            .apply(money)
        )


        st.dataframe(
            koc_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # BRAND ANALYSIS
        # =================================================

        st.divider()

        st.subheader(
            "📊 Phân tích Brand"
        )


        brand_analysis = (
            month_data
            .groupby(
                "store_name",
                as_index=False
            )
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum"),
                KOC=("creator_name", "nunique")
            )
        )


        brand_analysis["Tỷ lệ hoa hồng"] = (
            brand_analysis["Hoa hồng thực tế"]
            / brand_analysis["GMV"]
            * 100
        ).fillna(0)


        brand_analysis = (
            brand_analysis
            .sort_values(
                "Hoa hồng thực tế",
                ascending=False
            )
        )


        analysis_display = (
            brand_analysis.copy()
        )


        analysis_display["GMV"] = (
            analysis_display["GMV"]
            .apply(money)
        )


        analysis_display["Hoa hồng thực tế"] = (
            analysis_display["Hoa hồng thực tế"]
            .apply(money)
        )


        st.dataframe(
            analysis_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # MONTHLY SUMMARY
        # =================================================

        st.divider()

        st.subheader(
            "📅 Tổng quan theo tháng"
        )


        monthly = (
            analytics_data
            .groupby(
                "report_month",
                as_index=False
            )
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum"),
                KOC=("creator_name", "nunique"),
                Brand=("store_name", "nunique")
            )
        )


        monthly["Tỷ lệ hoa hồng"] = (
            monthly["Hoa hồng thực tế"]
            / monthly["GMV"]
            * 100
        ).fillna(0)


        monthly_display = monthly.copy()


        monthly_display["GMV"] = (
            monthly_display["GMV"]
            .apply(money)
        )


        monthly_display["Hoa hồng thực tế"] = (
            monthly_display["Hoa hồng thực tế"]
            .apply(money)
        )


        st.dataframe(
            monthly_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # DETAIL
        # =================================================

        with st.expander(
            "🔍 Xem dữ liệu chi tiết"
        ):

            detail = month_data[
                [
                    "report_date",
                    "creator_name",
                    "store_name",
                    "gmv",
                    "ac"
                ]
            ].copy()


            detail["report_date"] = (
                pd.to_datetime(
                    detail["report_date"],
                    errors="coerce"
                )
                .dt.strftime("%d/%m/%Y")
            )


            detail["gmv"] = (
                detail["gmv"]
                .apply(money)
            )


            detail["ac"] = (
                detail["ac"]
                .apply(money)
            )


            detail.columns = [
                "Ngày",
                "KOC/NST",
                "Brand",
                "GMV",
                "Hoa hồng thực tế"
            ]


            st.dataframe(
                detail,
                use_container_width=True,
                hide_index=True
            )


        # =================================================
        # DOWNLOAD
        # =================================================

        csv = (
            month_data
            .to_csv(
                index=False
            )
            .encode("utf-8-sig")
        )


        st.download_button(
            "📥 Xuất dữ liệu tháng",
            data=csv,
            file_name=(
                f"analytics_{selected_month}.csv"
            ),
            mime="text/csv"
        )
