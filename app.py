import streamlit as st
import sqlite3
import pandas as pd

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("koc_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS koc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    phone TEXT,
    name TEXT,
    follower INTEGER,
    category TEXT,
    note TEXT
)
""")

conn.commit()


# =========================
# WEB
# =========================

st.set_page_config(
    page_title="KOC Management",
    page_icon="📊",
    layout="wide"
)

st.title("📊 KOC Management & Analytics")
st.write("Hệ thống quản lý KOC/KOL")

st.divider()


# =========================
# MENU
# =========================

page = st.sidebar.radio(
    "MENU",
    [
        "🏠 Dashboard",
        "👤 KOC Database"
    ]
)


# =========================
# DASHBOARD
# =========================

if page == "🏠 Dashboard":

    total_koc = pd.read_sql(
        "SELECT COUNT(*) AS total FROM koc",
        conn
    ).iloc[0]["total"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tổng KOC", total_koc)

    with col2:
        st.metric("Tổng Brand", 0)

    with col3:
        st.metric("Tổng GMV", "0 VNĐ")

    st.info("🚀 Database KOC đã được khởi tạo.")


# =========================
# KOC DATABASE
# =========================

elif page == "👤 KOC Database":

    st.header("👤 KOC Database")

    tab1, tab2 = st.tabs([
        "➕ Thêm KOC",
        "🔍 Kiểm tra KOC"
    ])


    # -------------------------
    # ADD KOC
    # -------------------------

    with tab1:

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

        if st.button("💾 Lưu KOC", type="primary"):

            username = username.strip()

            if not username:
                st.error("Vui lòng nhập username.")
            else:

                if not username.startswith("@"):
                    username = "@" + username

                try:

                    cursor.execute("""
                    INSERT INTO koc
                    (username, phone, name, follower, category, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        username,
                        phone,
                        name,
                        follower,
                        category,
                        note
                    ))

                    conn.commit()

                    st.success(
                        f"Đã lưu {username} vào database!"
                    )

                except sqlite3.IntegrityError:

                    st.warning(
                        f"{username} đã tồn tại trong database."
                    )


    # =========================
# CHECK KOC - BULK
# =========================

with tab2:

    st.subheader("🔍 Kiểm tra hàng loạt KOC")

    usernames = st.text_area(
        "Paste username - mỗi dòng 1 username",
        placeholder="@abc\n@xyz\n@mymy",
        height=180
    )

    if st.button("🔎 Kiểm tra danh sách", type="primary"):

        if not usernames.strip():

            st.warning("Vui lòng nhập ít nhất 1 username.")

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
                SELECT username, phone, name,
                       follower, category
                FROM koc
                WHERE username IN ({placeholders})
            """

            result = pd.read_sql(
                query,
                conn,
                params=username_list
            )

            found = set(result["username"])

            output = []

            for username in username_list:

                if username in found:

                    row = result[
                        result["username"] == username
                    ].iloc[0]

                    output.append({
                        "Username": username,
                        "Trạng thái": "✅ ĐÃ CÓ",
                        "Số điện thoại": row["phone"],
                        "Tên": row["name"],
                        "Follower": row["follower"],
                        "Category": row["category"]
                    })

                else:

                    output.append({
                        "Username": username,
                        "Trạng thái": "❌ CHƯA CÓ",
                        "Số điện thoại": "",
                        "Tên": "",
                        "Follower": "",
                        "Category": ""
                    })

            output_df = pd.DataFrame(output)

            # KPI
            total = len(output_df)
            found_count = len(output_df[
                output_df["Trạng thái"] == "✅ ĐÃ CÓ"
            ])
            not_found_count = total - found_count

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Tổng kiểm tra", total)

            with col2:
                st.metric("✅ Đã có", found_count)

            with col3:
                st.metric("❌ Chưa có", not_found_count)

            st.divider()

            st.dataframe(
                output_df,
                use_container_width=True,
                hide_index=True
            )

            # Chỉ lấy những KOC đã có SĐT
            phone_list = output_df[
                output_df["Trạng thái"] == "✅ ĐÃ CÓ"
            ]["Số điện thoại"].dropna()

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
