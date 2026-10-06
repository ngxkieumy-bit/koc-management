import streamlit as st
import sqlite3
import pandas as pd


# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect("koc_data.db", check_same_thread=False)
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

conn.commit()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="KOC Management",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# HEADER
# =========================================================

st.title("📊 KOC Management & Analytics")
st.write("Hệ thống quản lý KOC/KOL và phân tích dữ liệu")

st.divider()


# =========================================================
# SIDEBAR
# =========================================================

page = st.sidebar.radio(
    "MENU",
    [
        "🏠 Dashboard",
        "👤 KOC Database"
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

    total_phone = pd.read_sql(
        """
        SELECT COUNT(*) AS total
        FROM koc
        WHERE phone IS NOT NULL
        AND phone != ''
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
            "📱 KOC có SĐT",
            int(total_phone)
        )

    with col3:
        st.metric(
            "🏷️ Ngành hàng",
            pd.read_sql(
                """
                SELECT COUNT(DISTINCT category) AS total
                FROM koc
                WHERE category IS NOT NULL
                AND category != ''
                """,
                conn
            ).iloc[0]["total"]
        )

    st.success("🚀 Hệ thống KOC đang hoạt động.")

    st.divider()

    st.subheader("📈 Tổng quan KOC")

    overview = pd.read_sql(
        """
        SELECT
            category AS "Ngành hàng",
            COUNT(*) AS "Số KOC"
        FROM koc
        GROUP BY category
        ORDER BY COUNT(*) DESC
        """,
        conn
    )

    if not overview.empty:
        st.dataframe(
            overview,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Chưa có dữ liệu KOC.")


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

        st.subheader("➕ Thêm KOC")

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
                        f"{username} đã tồn tại trong database."
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
                    "Vui lòng nhập ít nhất 1 username."
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

                output_df = pd.DataFrame(output)

                total = len(output_df)

                found_count = len(
                    output_df[
                        output_df["Trạng thái"] == "✅ ĐÃ CÓ"
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

                st.divider()

                st.dataframe(
                    output_df,
                    use_container_width=True,
                    hide_index=True
                )

                phone_list = output_df[
                    output_df["Trạng thái"] == "✅ ĐÃ CÓ"
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
    # TAB 3 - IMPORT EXCEL
    # =====================================================

    with tab3:

        st.subheader(
            "📥 Import KOC từ Excel"
        )

        st.write(
            "File Excel cần có ít nhất cột:"
        )

        st.markdown(
            "**username** và **phone**"
        )

        st.write(
            "Có thể thêm:"
        )

        st.markdown(
            "**name, follower, category, note**"
        )

        uploaded_file = st.file_uploader(
            "Chọn file Excel",
            type=["xlsx", "xls"]
        )

        if uploaded_file is not None:

            try:

                import_df = pd.read_excel(
                    uploaded_file
                )

                st.write(
                    "📋 Preview dữ liệu:"
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
                        "File đang thiếu cột: "
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
                                row.get(
                                    "phone",
                                    ""
                                )
                            ).strip()

                            if phone == "nan":
                                phone = ""

                            name_value = str(
                                row.get(
                                    "name",
                                    ""
                                )
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
                            f"➕ {added} KOC mới | "
                            f"🔄 {updated} KOC cập nhật | "
                            f"⚠️ {skipped} dòng bỏ qua"
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
                placeholder="Username / tên / số điện thoại"
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

        st.divider()

        display_df = filtered[
            [
                "username",
                "phone",
                "name",
                "follower",
                "category",
                "note"
            ]
        ].copy()

        display_df.columns = [
            "Username",
            "Số điện thoại",
            "Tên KOC",
            "Follower",
            "Ngành hàng",
            "Ghi chú"
        ]

        st.dataframe(
            display_df,
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
