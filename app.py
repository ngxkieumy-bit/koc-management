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


# =========================================================
# CREATE TABLES
# =========================================================

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
    campaign_id TEXT,
    campaign_name TEXT,
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
# HELPER FUNCTIONS
# =========================================================

def money(value):
    return f"{value:,.0f} đ"


def percent(value):
    return f"{value:.2f}%"


def clean_number(series):
    """
    Làm sạch số tiền:
    100,000,000
    100000000
    100.000.000
    100000000 ₫
    """

    return (
        series
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace("₫", "", regex=False)
        .str.replace("đ", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
        .replace(
            ["", "nan", "None", "NaN"],
            "0"
        )
        .pipe(
            pd.to_numeric,
            errors="coerce"
        )
        .fillna(0)
    )


def parse_tiktok_date(value):

    if pd.isna(value):
        return pd.NaT

    # Nếu đã là Timestamp
    if isinstance(value, pd.Timestamp):
        return value

    # Nếu là datetime
    if hasattr(value, "year") and hasattr(value, "month"):

        try:
            return pd.Timestamp(value)
        except Exception:
            pass

    # Nếu là Excel serial date
    if isinstance(value, (int, float)):

        try:

            number = float(value)

            if 20000 < number < 60000:

                return (
                    pd.Timestamp("1899-12-30")
                    + pd.to_timedelta(
                        number,
                        unit="D"
                    )
                )

        except Exception:
            pass

    # Nếu là text
    value = str(value).strip()

    if not value:
        return pd.NaT

    formats = [
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S"
    ]

    for fmt in formats:

        try:

            result = pd.to_datetime(
                value,
                format=fmt,
                errors="coerce"
            )

            if pd.notna(result):
                return result

        except Exception:
            pass

    # Cuối cùng thử pandas
    try:

        result = pd.to_datetime(
            value,
            dayfirst=True,
            errors="coerce"
        )

        if pd.notna(result):
            return result

    except Exception:
        pass

    return pd.NaT


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
# SIDEBAR
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

    total_months = pd.read_sql(
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
            int(total_months)
        )

    st.success(
        "🚀 Hệ thống KOC đang hoạt động."
    )

    st.divider()

    st.subheader(
        "📈 Tổng quan Analytics"
    )

    analytics_df = pd.read_sql(
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

    if analytics_df.empty:

        st.info(
            "Chưa có dữ liệu Analytics. "
            "Vào 📊 Monthly Analytics để upload file TikTok."
        )

    else:

        analytics_df["AC / GMV (%)"] = (
            analytics_df["ac"]
            / analytics_df["gmv"]
            * 100
        ).fillna(0)

        analytics_df["GMV"] = (
            analytics_df["gmv"]
            .apply(money)
        )

        analytics_df["AC"] = (
            analytics_df["ac"]
            .apply(money)
        )

        display = analytics_df[
            [
                "report_month",
                "GMV",
                "AC",
                "AC / GMV (%)"
            ]
        ].copy()

        display.columns = [
            "Tháng",
            "GMV",
            "AC",
            "AC / GMV (%)"
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
    # TAB 1 - ADD KOC
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
                        f"{username} đã tồn tại."
                    )


    # =====================================================
    # TAB 2 - BULK CHECK
    # =====================================================

    with tab2:

        st.subheader(
            "🔍 Kiểm tra hàng loạt KOC"
        )

        usernames = st.text_area(
            "Paste username - mỗi dòng 1 username",
            placeholder="@abc\n@xyz\n@mymy",
            height=180
        )

        if st.button(
            "🔎 Kiểm tra danh sách",
            type="primary"
        ):

            if not usernames.strip():

                st.warning(
                    "Vui lòng nhập username."
                )

            else:

                username_list = []

                for username in usernames.splitlines():

                    username = username.strip()

                    if username:

                        if not username.startswith("@"):
                            username = "@" + username

                        if username not in username_list:
                            username_list.append(username)

                placeholders = ",".join(
                    ["?"] * len(username_list)
                )

                query = f"""
                    SELECT
                        username,
                        phone,
                        name,
                        follower,
                        category
                    FROM koc
                    WHERE username IN ({placeholders})
                """

                result = pd.read_sql(
                    query,
                    conn,
                    params=username_list
                )

                found = set(
                    result["username"].tolist()
                )

                output = []

                for username in username_list:

                    if username in found:

                        row = result[
                            result["username"] == username
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

                total = len(output_df)

                found_count = len(
                    output_df[
                        output_df["Trạng thái"]
                        == "✅ ĐÃ CÓ"
                    ]
                )

                not_found_count = (
                    total - found_count
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Tổng kiểm tra",
                        total
                    )

                with col2:

                    st.metric(
                        "✅ Đã có",
                        found_count
                    )

                with col3:

                    st.metric(
                        "❌ Chưa có",
                        not_found_count
                    )

                st.dataframe(
                    output_df,
                    use_container_width=True,
                    hide_index=True
                )

                phone_list = output_df[
                    output_df["Trạng thái"]
                    == "✅ ĐÃ CÓ"
                ]["Số điện thoại"]

                phone_text = "\n".join(
                    str(phone)
                    for phone in phone_list
                    if str(phone).strip()
                )

                if phone_text:

                    st.text_area(
                        "📱 Danh sách SĐT",
                        phone_text,
                        height=150
                    )


    # =====================================================
    # TAB 3 - IMPORT KOC
    # =====================================================

    with tab3:

        st.subheader(
            "📥 Import KOC từ Excel"
        )

        st.write(
            "Cần có: **username, phone**"
        )

        uploaded_file = st.file_uploader(
            "Chọn file Excel",
            type=["xlsx", "xls"],
            key="koc_upload"
        )

        if uploaded_file is not None:

            try:

                import_df = pd.read_excel(
                    uploaded_file
                )

                st.dataframe(
                    import_df.head(10),
                    use_container_width=True,
                    hide_index=True
                )

                required_columns = [
                    "username",
                    "phone"
                ]

                missing_columns = [
                    col
                    for col in required_columns
                    if col not in import_df.columns
                ]

                if missing_columns:

                    st.error(
                        "Thiếu cột: "
                        + ", ".join(
                            missing_columns
                        )
                    )

                else:

                    if st.button(
                        "🚀 Import vào Database",
                        type="primary"
                    ):

                        added = 0
                        updated = 0
                        skipped = 0

                        for _, row in import_df.iterrows():

                            username = str(
                                row["username"]
                            ).strip()

                            if (
                                not username
                                or username == "nan"
                            ):

                                skipped += 1
                                continue

                            if not username.startswith("@"):
                                username = "@" + username

                            phone = str(
                                row["phone"]
                            ).strip()

                            if phone == "nan":
                                phone = ""

                            name_value = str(
                                row.get("name", "")
                            ).strip()

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
                            ).strip()

                            if category_value == "nan":
                                category_value = "Other"

                            note_value = str(
                                row.get(
                                    "note",
                                    ""
                                )
                            ).strip()

                            if note_value == "nan":
                                note_value = ""

                            existing = cursor.execute(
                                """
                                SELECT id
                                FROM koc
                                WHERE username = ?
                                """,
                                (username,)
                            ).fetchone()

                            if existing:

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
                                        int(
                                            follower_value
                                        ),
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
                                        int(
                                            follower_value
                                        ),
                                        category_value,
                                        note_value
                                    )
                                )

                                added += 1

                        conn.commit()

                        st.success(
                            f"Import thành công! "
                            f"➕ {added} mới | "
                            f"🔄 {updated} cập nhật | "
                            f"⚠️ {skipped} bỏ qua"
                        )

            except Exception as e:

                st.error(
                    f"Không thể đọc file: {e}"
                )


    # =====================================================
    # TAB 4 - KOC LIST
    # =====================================================

    with tab4:

        st.subheader(
            "📋 Danh sách KOC"
        )

        all_koc = pd.read_sql(
            """
            SELECT
                id,
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

        col1, col2 = st.columns(2)

        with col1:

            search = st.text_input(
                "🔎 Tìm KOC",
                placeholder="Username / tên / SĐT"
            )

        with col2:

            categories = (
                ["Tất cả"]
                + sorted(
                    all_koc["category"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

            category_filter = st.selectbox(
                "🏷️ Ngành hàng",
                categories
            )

        filtered = all_koc.copy()

        if search.strip():

            search_text = (
                search.strip().lower()
            )

            filtered = filtered[
                filtered["username"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_text,
                    na=False
                )
                |
                filtered["name"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_text,
                    na=False
                )
                |
                filtered["phone"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_text,
                    na=False
                )
            ]

        if category_filter != "Tất cả":

            filtered = filtered[
                filtered["category"]
                == category_filter
            ]

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "👤 Tổng KOC",
                len(all_koc)
            )

        with col2:

            st.metric(
                "🔎 Kết quả",
                len(filtered)
            )

        with col3:

            phone_count = (
                filtered["phone"]
                .fillna("")
                .astype(str)
                .str.strip()
                .ne("")
                .sum()
            )

            st.metric(
                "📱 Có SĐT",
                int(phone_count)
            )

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        csv = filtered.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "📥 Xuất danh sách KOC",
            data=csv,
            file_name="koc_database.csv",
            mime="text/csv"
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
            "Ghi chú",
            placeholder="Beauty / TikTok Shop / Campaign tháng 10"
        )

        if st.button(
            "💾 Lưu Brand",
            type="primary"
        ):

            brand_name = brand_name.strip()

            if not brand_name:

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
                            brand_name,
                            float(commission),
                            float(target_gmv),
                            note.strip()
                        )
                    )

                    conn.commit()

                    st.success(
                        f"Đã lưu Brand: {brand_name}"
                    )

                except sqlite3.IntegrityError:

                    st.warning(
                        f"Brand '{brand_name}' đã tồn tại."
                    )


    # =====================================================
    # IMPORT BRAND
    # =====================================================

    with tab2:

        st.subheader(
            "📥 Import Brand từ Excel"
        )

        st.write(
            "Cần có: **brand_name, commission, target_gmv**"
        )

        uploaded_brand_file = st.file_uploader(
            "Chọn file Excel Brand",
            type=["xlsx", "xls"],
            key="brand_upload"
        )

        if uploaded_brand_file is not None:

            try:

                brand_df = pd.read_excel(
                    uploaded_brand_file
                )

                st.dataframe(
                    brand_df.head(10),
                    use_container_width=True,
                    hide_index=True
                )

                required_columns = [
                    "brand_name",
                    "commission",
                    "target_gmv"
                ]

                missing_columns = [
                    col
                    for col in required_columns
                    if col not in brand_df.columns
                ]

                if missing_columns:

                    st.error(
                        "Thiếu cột: "
                        + ", ".join(
                            missing_columns
                        )
                    )

                else:

                    if st.button(
                        "🚀 Import Brand",
                        type="primary"
                    ):

                        added = 0
                        updated = 0

                        for _, row in brand_df.iterrows():

                            brand_name = str(
                                row["brand_name"]
                            ).strip()

                            if not brand_name:
                                continue

                            commission_value = row[
                                "commission"
                            ]

                            target_gmv_value = row[
                                "target_gmv"
                            ]

                            if pd.isna(
                                commission_value
                            ):
                                commission_value = 0

                            if pd.isna(
                                target_gmv_value
                            ):
                                target_gmv_value = 0

                            note_value = str(
                                row.get("note", "")
                            ).strip()

                            existing = cursor.execute(
                                """
                                SELECT id
                                FROM brands
                                WHERE brand_name = ?
                                """,
                                (brand_name,)
                            ).fetchone()

                            if existing:

                                cursor.execute(
                                    """
                                    UPDATE brands
                                    SET
                                        commission = ?,
                                        target_gmv = ?,
                                        note = ?
                                    WHERE brand_name = ?
                                    """,
                                    (
                                        float(
                                            commission_value
                                        ),
                                        float(
                                            target_gmv_value
                                        ),
                                        note_value,
                                        brand_name
                                    )
                                )

                                updated += 1

                            else:

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
                                        brand_name,
                                        float(
                                            commission_value
                                        ),
                                        float(
                                            target_gmv_value
                                        ),
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
    # BRAND LIST
    # =====================================================

    with tab3:

        st.subheader(
            "📋 Danh sách Brand"
        )

        all_brands = pd.read_sql(
            """
            SELECT
                id,
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
            "🔎 Tìm Brand",
            placeholder="Nhập tên Brand"
        )

        filtered_brands = all_brands.copy()

        if search_brand.strip():

            search_text = (
                search_brand.strip().lower()
            )

            filtered_brands = filtered_brands[
                filtered_brands["brand_name"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_text,
                    na=False
                )
            ]

        total_brand = len(
            all_brands
        )

        result_brand = len(
            filtered_brands
        )

        total_target = (
            filtered_brands["target_gmv"]
            .sum()
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "🏷️ Tổng Brand",
                total_brand
            )

        with col2:

            st.metric(
                "🔎 Kết quả",
                result_brand
            )

        with col3:

            st.metric(
                "🎯 Tổng GMV mục tiêu",
                money(total_target)
            )

        display_brand = filtered_brands.copy()

        display_brand["TAP dự kiến nhận"] = (
            display_brand["target_gmv"]
            * display_brand["commission"]
            / 100
        )

        display_brand.columns = [
            "ID",
            "Brand",
            "Commission (%)",
            "GMV mục tiêu",
            "Ghi chú",
            "TAP dự kiến nhận"
        ]

        display_brand = display_brand[
            [
                "Brand",
                "Commission (%)",
                "GMV mục tiêu",
                "TAP dự kiến nhận",
                "Ghi chú"
            ]
        ]

        st.dataframe(
            display_brand,
            use_container_width=True,
            hide_index=True
        )

        csv = filtered_brands.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "📥 Xuất danh sách Brand",
            data=csv,
            file_name="brand_database.csv",
            mime="text/csv"
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
        "A = Ngày | "
        "F = KOC/NST | "
        "L = Brand | "
        "M = GMV | "
        "AC = Hoa hồng TAP"
    )

    st.divider()


    # =====================================================
    # UPLOAD FILE
    # =====================================================

    st.subheader(
        "📥 Upload báo cáo TikTok"
    )

    analytics_file = st.file_uploader(
        "Chọn file Custom Report TikTok",
        type=["xlsx", "xls"],
        key="analytics_upload"
    )


    if analytics_file is not None:

        try:

            # =================================================
            # CHỈ ĐỌC 7 CỘT CẦN THIẾT
            #
            # A = Ngày
            # C = Campaign ID
            # D = Campaign Name
            # F = KOC/NST
            # L = Brand
            # M = GMV
            # AC = AC
            # =================================================

            raw_df = pd.read_excel(
                analytics_file,
                usecols="A,C,D,F,L,M,AC"
            )

            st.success(
                f"Đã đọc {len(raw_df):,} dòng dữ liệu."
            )


            # =================================================
            # MAP 7 CỘT SAU KHI READ
            # =================================================

            date_col = raw_df.iloc[:, 0]

            campaign_id_col = raw_df.iloc[:, 1]

            campaign_name_col = raw_df.iloc[:, 2]

            creator_col = raw_df.iloc[:, 3]

            store_col = raw_df.iloc[:, 4]

            gmv_col = raw_df.iloc[:, 5]

            ac_col = raw_df.iloc[:, 6]


            # =================================================
            # PREPARE DATA
            # =================================================

            analytics_upload = pd.DataFrame()


            # Ngày
            analytics_upload["report_date"] = (
                date_col.apply(
                    parse_tiktok_date
                )
            )


            # Campaign ID
            analytics_upload["campaign_id"] = (
                campaign_id_col
                .fillna("")
                .astype(str)
                .str.strip()
            )


            # Campaign Name
            analytics_upload["campaign_name"] = (
                campaign_name_col
                .fillna("")
                .astype(str)
                .str.strip()
            )


            # KOC/NST
            analytics_upload["creator_name"] = (
                creator_col
                .fillna("")
                .astype(str)
                .str.strip()
            )


            # Brand
            analytics_upload["store_name"] = (
                store_col
                .fillna("")
                .astype(str)
                .str.strip()
            )


            # GMV = M
            analytics_upload["gmv"] = clean_number(
                gmv_col
            )


            # AC = AC
            analytics_upload["ac"] = clean_number(
                ac_col
            )


            # =================================================
            # REMOVE ROWS WITHOUT DATE
            # =================================================

            analytics_upload = analytics_upload[
                analytics_upload["report_date"].notna()
            ].copy()


            # =================================================
            # CREATE MONTH
            # =================================================

            analytics_upload["report_month"] = (
                analytics_upload["report_date"]
                .dt.to_period("M")
                .astype(str)
            )


            # =================================================
            # CHECK DATA
            # =================================================

            if analytics_upload.empty:

                st.error(
                    "❌ Không đọc được cột Ngày. "
                    "Hãy kiểm tra lại cột A trong file TikTok."
                )

            else:

                st.success(
                    f"✅ Đã xử lý "
                    f"{len(analytics_upload):,} dòng hợp lệ."
                )


                # =================================================
                # PREVIEW
                # =================================================

                st.subheader(
                    "👀 Preview dữ liệu"
                )

                preview = analytics_upload[
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
                    "AC"
                ]


                st.dataframe(
                    preview,
                    use_container_width=True,
                    hide_index=True
                )


                # =================================================
                # MONTHS
                # =================================================

                months_in_file = sorted(
                    analytics_upload[
                        "report_month"
                    ].unique()
                )


                st.write(
                    "📅 Tháng phát hiện trong file:",
                    ", ".join(
                        months_in_file
                    )
                )


                # =================================================
                # FILE SUMMARY
                # =================================================

                file_gmv = (
                    analytics_upload["gmv"]
                    .sum()
                )

                file_ac = (
                    analytics_upload["ac"]
                    .sum()
                )

                file_rate = (
                    file_ac
                    / file_gmv
                    * 100
                    if file_gmv != 0
                    else 0
                )


                col1, col2, col3 = st.columns(3)


                with col1:

                    st.metric(
                        "💰 GMV trong file",
                        money(file_gmv)
                    )


                with col2:

                    st.metric(
                        "💵 AC trong file",
                        money(file_ac)
                    )


                with col3:

                    st.metric(
                        "📊 AC / GMV",
                        percent(file_rate)
                    )


                st.divider()


                # =================================================
                # IMPORT
                # =================================================

                st.subheader(
                    "🚀 Import vào hệ thống"
                )


                st.warning(
                    "Nếu tháng đã tồn tại trong Database, "
                    "hệ thống sẽ XÓA dữ liệu cũ của tháng đó "
                    "rồi import dữ liệu mới để tránh bị nhân đôi."
                )


                if st.button(
                    "🚀 Import dữ liệu Analytics",
                    type="primary"
                ):

                    # =================================================
                    # DELETE OLD MONTHS
                    # =================================================

                    for month in months_in_file:

                        cursor.execute(
                            """
                            DELETE FROM analytics
                            WHERE report_month = ?
                            """,
                            (month,)
                        )


                    # =================================================
                    # PREPARE BULK INSERT
                    # =================================================

                    insert_data = []

                    for row in analytics_upload.itertuples(
                        index=False
                    ):

                        insert_data.append(
                            (
                                row.report_date.strftime(
                                    "%Y-%m-%d"
                                ),
                                row.report_month,
                                row.campaign_id,
                                row.campaign_name,
                                row.creator_name,
                                row.store_name,
                                float(row.gmv),
                                float(row.ac)
                            )
                        )


                    # =================================================
                    # FAST INSERT
                    # =================================================

                    cursor.executemany(
                        """
                        INSERT INTO analytics
                        (
                            report_date,
                            report_month,
                            campaign_id,
                            campaign_name,
                            creator_name,
                            store_name,
                            gmv,
                            ac
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        insert_data
                    )


                    conn.commit()


                    st.success(
                        f"🎉 Import thành công "
                        f"{len(insert_data):,} dòng!"
                    )


                    st.rerun()


        except Exception as e:

            st.error(
                f"❌ Không thể đọc file: {e}"
            )


    # =====================================================
    # LOAD ANALYTICS DATABASE
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
        # FILTER
        # =================================================

        col1, col2 = st.columns(2)


        with col1:

            month_options = sorted(
                analytics_data[
                    "report_month"
                ]
                .dropna()
                .unique(),
                reverse=True
            )

            selected_month = st.selectbox(
                "📅 Chọn tháng",
                month_options
            )


        with col2:

            brand_options = [
                "Tất cả"
            ] + sorted(
                analytics_data[
                    analytics_data[
                        "report_month"
                    ]
                    == selected_month
                ]["store_name"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_brand = st.selectbox(
                "🏷️ Chọn Brand",
                brand_options
            )


        # =================================================
        # FILTER DATA
        # =================================================

        dashboard_df = analytics_data[
            analytics_data["report_month"]
            == selected_month
        ].copy()


        if selected_brand != "Tất cả":

            dashboard_df = dashboard_df[
                dashboard_df["store_name"]
                == selected_brand
            ]


        # =================================================
        # KPI
        # =================================================

        total_gmv = (
            dashboard_df["gmv"]
            .sum()
        )

        total_ac = (
            dashboard_df["ac"]
            .sum()
        )

        ac_percent = (
            total_ac
            / total_gmv
            * 100
            if total_gmv != 0
            else 0
        )


        kpi_default = 10000000.0


        col1, col2, col3, col4 = st.columns(4)


        with col1:

            st.metric(
                "💰 Tổng GMV",
                money(total_gmv)
            )


        with col2:

            st.metric(
                "💵 Tổng AC",
                money(total_ac)
            )


        with col3:

            st.metric(
                "📊 AC / GMV",
                percent(ac_percent)
            )


        with col4:

            kpi = st.number_input(
                "🎯 KPI",
                min_value=0.0,
                value=kpi_default,
                step=1000000.0
            )

            achievement = (
                total_ac
                / kpi
                * 100
                if kpi > 0
                else 0
            )

            st.metric(
                "% đạt KPI",
                percent(achievement)
            )


        # =================================================
        # TOP BRAND + TOP KOC
        # =================================================

        st.divider()


        col1, col2 = st.columns(2)


        # =================================================
        # TOP BRAND
        # =================================================

        with col1:

            st.subheader(
                "🏆 Top Brand theo AC"
            )


            top_brand = (
                dashboard_df
                .groupby(
                    "store_name",
                    as_index=False
                )
                .agg(
                    GMV=("gmv", "sum"),
                    AC=("ac", "sum")
                )
                .sort_values(
                    "AC",
                    ascending=False
                )
                .head(10)
            )


            if not top_brand.empty:

                top_brand[
                    "AC / GMV (%)"
                ] = (
                    top_brand["AC"]
                    / top_brand["GMV"]
                    * 100
                ).fillna(0)


                top_brand_display = (
                    top_brand.copy()
                )


                top_brand_display["GMV"] = (
                    top_brand_display["GMV"]
                    .apply(money)
                )


                top_brand_display["AC"] = (
                    top_brand_display["AC"]
                    .apply(money)
                )


                st.dataframe(
                    top_brand_display,
                    use_container_width=True,
                    hide_index=True
                )


        # =================================================
        # TOP KOC
        # =================================================

        with col2:

            st.subheader(
                "👑 Top KOC/NST theo AC"
            )


            top_creator = (
                dashboard_df
                .groupby(
                    "creator_name",
                    as_index=False
                )
                .agg(
                    GMV=("gmv", "sum"),
                    AC=("ac", "sum")
                )
                .sort_values(
                    "AC",
                    ascending=False
                )
                .head(10)
            )


            top_creator_display = (
                top_creator.copy()
            )


            top_creator_display["GMV"] = (
                top_creator_display["GMV"]
                .apply(money)
            )


            top_creator_display["AC"] = (
                top_creator_display["AC"]
                .apply(money)
            )


            st.dataframe(
                top_creator_display,
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
            dashboard_df
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


        brand_analysis[
            "AC / GMV (%)"
        ] = (
            brand_analysis["AC"]
            / brand_analysis["GMV"]
            * 100
        ).fillna(0)


        brand_analysis = (
            brand_analysis
            .sort_values(
                "AC",
                ascending=False
            )
        )


        brand_display = (
            brand_analysis.copy()
        )


        brand_display["GMV"] = (
            brand_display["GMV"]
            .apply(money)
        )


        brand_display["AC"] = (
            brand_display["AC"]
            .apply(money)
        )


        st.dataframe(
            brand_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # MONTHLY SUMMARY
        # =================================================

        st.divider()

        st.subheader(
            "📅 Tổng quan các tháng"
        )


        monthly_summary = (
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


        monthly_summary[
            "AC / GMV (%)"
        ] = (
            monthly_summary["AC"]
            / monthly_summary["GMV"]
            * 100
        ).fillna(0)


        monthly_summary = (
            monthly_summary
            .sort_values(
                "report_month",
                ascending=False
            )
        )


        monthly_display = (
            monthly_summary.copy()
        )


        monthly_display["GMV"] = (
            monthly_display["GMV"]
            .apply(money)
        )


        monthly_display["AC"] = (
            monthly_display["AC"]
            .apply(money)
        )


        monthly_display.columns = [
            "Tháng",
            "GMV",
            "AC",
            "KOC",
            "Brand",
            "AC / GMV (%)"
        ]


        st.dataframe(
            monthly_display,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # RAW DATA
        # =================================================

        st.divider()

        with st.expander(
            "🔍 Xem dữ liệu chi tiết"
        ):

            detail_display = dashboard_df[
                [
                    "report_date",
                    "creator_name",
                    "store_name",
                    "gmv",
                    "ac",
                    "campaign_name"
                ]
            ].copy()


            detail_display["report_date"] = (
                pd.to_datetime(
                    detail_display[
                        "report_date"
                    ]
                ).dt.strftime(
                    "%d/%m/%Y"
                )
            )


            detail_display["gmv"] = (
                detail_display["gmv"]
                .apply(money)
            )


            detail_display["ac"] = (
                detail_display["ac"]
                .apply(money)
            )


            detail_display.columns = [
                "Ngày",
                "KOC/NST",
                "Brand",
                "GMV",
                "AC",
                "Campaign"
            ]


            st.dataframe(
                detail_display,
                use_container_width=True,
                hide_index=True
            )


        # =================================================
        # DOWNLOAD
        # =================================================

        csv = dashboard_df.to_csv(
            index=False
        ).encode("utf-8-sig")


        st.download_button(
            "📥 Xuất dữ liệu tháng",
            data=csv,
            file_name=(
                f"analytics_{selected_month}.csv"
            ),
            mime="text/csv"
        )
