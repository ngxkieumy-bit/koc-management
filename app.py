import streamlit as st
import sqlite3
import pandas as pd
from datetime import date


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


cursor.execute("""
CREATE TABLE IF NOT EXISTS tap_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_month TEXT UNIQUE,
    target_ac REAL DEFAULT 0,
    note TEXT
)
""")




cursor.execute("""
CREATE TABLE IF NOT EXISTS booking_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_month TEXT,
    brand_name TEXT,
    service_group TEXT,
    package_name TEXT,
    tier TEXT,
    contract_fee REAL DEFAULT 0,
    running INTEGER DEFAULT 0,
    paid INTEGER DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    koc_paid_amount REAL DEFAULT 0,
    note TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS total_revenue_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_month TEXT UNIQUE,
    target_revenue REAL DEFAULT 0,
    note TEXT
)
""")


# =========================================================
# DATABASE MIGRATION
# =========================================================
# Nếu bảng booking_services đã tồn tại từ bản cũ thì tự thêm
# cột tiền KOC đã thanh toán, không làm mất dữ liệu cũ.
# =========================================================

booking_columns = [
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(booking_services)"
    ).fetchall()
]

if "koc_paid_amount" not in booking_columns:
    cursor.execute(
        """
        ALTER TABLE booking_services
        ADD COLUMN koc_paid_amount REAL DEFAULT 0
        """
    )

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


def get_target_cycle(month_text):
    """
    Công ty tính Target theo chu kỳ 2 tháng:
    09-10, 11-12, 01-02, 03-04, ...
    """
    year, month = map(int, str(month_text).split("-"))

    if month % 2 == 1:
        start_month = month
        end_month = month + 1
    else:
        start_month = month - 1
        end_month = month

    # Xử lý trường hợp tháng 12.
    if end_month == 13:
        start_month = 11
        end_month = 12

    cycle_start = f"{year:04d}-{start_month:02d}"
    cycle_end = f"{year:04d}-{end_month:02d}"

    return cycle_start, cycle_end, f"{start_month:02d}/{year} - {end_month:02d}/{year}"


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
        "📦 Booking Service",
        "📊 Monthly Analytics",
        "🎯 TAP Target"
    ]
)


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.header("🏠 Dashboard tổng")
    st.write(
        "Tổng quan hiệu quả KOC/KOL, Brand, TAP và doanh thu Booking."
    )

    total_koc = int(
        pd.read_sql(
            "SELECT COUNT(*) AS total FROM koc",
            conn
        ).iloc[0]["total"]
    )

    total_brand = int(
        pd.read_sql(
            "SELECT COUNT(*) AS total FROM brands",
            conn
        ).iloc[0]["total"]
    )

    analytics_all = pd.read_sql(
        """
        SELECT
            report_date,
            report_month,
            creator_name,
            store_name,
            gmv,
            ac
        FROM analytics
        """,
        conn
    )

    booking_all = pd.read_sql(
        """
        SELECT
            id,
            contract_month,
            brand_name,
            service_group,
            package_name,
            tier,
            contract_fee,
            running,
            paid,
            paid_amount,
            koc_paid_amount,
            note
        FROM booking_services
        """,
        conn
    )

    revenue_targets = pd.read_sql(
        """
        SELECT
            target_month,
            target_revenue,
            note
        FROM total_revenue_targets
        """,
        conn
    )

    analytics_months = (
        set(analytics_all["report_month"].dropna().astype(str))
        if not analytics_all.empty
        else set()
    )

    booking_months = (
        set(booking_all["contract_month"].dropna().astype(str))
        if not booking_all.empty
        else set()
    )

    all_months = sorted(
        analytics_months | booking_months,
        reverse=True
    )

    if not all_months:

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("👤 Tổng KOC", f"{total_koc:,}")

        with c2:
            st.metric("🏷️ Tổng Brand", f"{total_brand:,}")

        with c3:
            st.metric("📅 Tháng dữ liệu", "0")

        st.info(
            "📌 Chưa có dữ liệu. Upload TikTok hoặc thêm Booking Service để bắt đầu."
        )

    else:

        selected_month = st.selectbox(
            "📅 Tháng báo cáo",
            all_months,
            key="dashboard_month"
        )

        current = analytics_all[
            analytics_all["report_month"].astype(str) == selected_month
        ].copy()

        current_booking = booking_all[
            booking_all["contract_month"].astype(str) == selected_month
        ].copy()

        current_gmv = (
            float(current["gmv"].sum())
            if not current.empty
            else 0.0
        )

        current_ac = (
            float(current["ac"].sum())
            if not current.empty
            else 0.0
        )

        current_rate = (
            current_ac / current_gmv * 100
            if current_gmv
            else 0
        )

        booking_contract_total = (
            float(current_booking["contract_fee"].sum())
            if not current_booking.empty
            else 0.0
        )

        booking_running_total = (
            float(
                current_booking.loc[
                    current_booking["running"] == 1,
                    "contract_fee"
                ].sum()
            )
            if not current_booking.empty
            else 0.0
        )

        booking_paid_total = (
            float(current_booking["paid_amount"].sum())
            if not current_booking.empty
            else 0.0
        )

        koc_paid_total = (
            float(current_booking["koc_paid_amount"].sum())
            if not current_booking.empty
            else 0.0
        )

        booking_unpaid_total = max(
            booking_contract_total - booking_paid_total,
            0
        )

        booking_net_revenue = max(
            booking_paid_total - koc_paid_total,
            0
        )

        total_revenue = current_ac + booking_net_revenue

        st.divider()

        k1, k2, k3, k4, k5 = st.columns(5)

        with k1:
            st.metric("👤 Tổng KOC", f"{total_koc:,}")

        with k2:
            st.metric("🏷️ Tổng Brand", f"{total_brand:,}")

        with k3:
            st.metric("💰 GMV", money(current_gmv))

        with k4:
            st.metric("💵 Hoa hồng thực tế", money(current_ac))

        with k5:
            st.metric("📊 Tỷ lệ hoa hồng", percent(current_rate))

        st.divider()
        st.subheader("💰 Doanh thu")

        booking_net_revenue = max(
            booking_paid_total - koc_paid_total,
            0
        )

        total_revenue = current_ac + booking_net_revenue

        r1, r2, r3 = st.columns(3)

        with r1:
            st.metric(
                "💵 Hoa hồng TAP",
                money(current_ac)
            )

        with r2:
            st.metric(
                "📦 Gói dịch vụ ròng",
                money(booking_net_revenue)
            )

        with r3:
            st.metric(
                "💰 Tổng doanh thu",
                money(total_revenue)
            )

        st.caption(
            "Gói dịch vụ ròng = Tiền khách đã thanh toán - Tiền KOC đã thanh toán. "
            "Tổng doanh thu = Hoa hồng TAP + Gói dịch vụ ròng."
        )

        # =====================================================
        # TARGET DOANH THU 2 THÁNG
        # =====================================================

        st.divider()
        st.subheader("🎯 Target tổng doanh thu (chu kỳ 2 tháng)")

        cycle_start, cycle_end, cycle_label = get_target_cycle(
            selected_month
        )

        cycle_months = [cycle_start, cycle_end]

        cycle_analytics = analytics_all[
            analytics_all["report_month"].astype(str).isin(
                cycle_months
            )
        ].copy()

        cycle_booking = booking_all[
            booking_all["contract_month"].astype(str).isin(
                cycle_months
            )
        ].copy()

        cycle_tap = (
            float(cycle_analytics["ac"].sum())
            if not cycle_analytics.empty
            else 0.0
        )

        cycle_booking_paid = (
            float(cycle_booking["paid_amount"].sum())
            if not cycle_booking.empty
            else 0.0
        )

        cycle_koc_paid = (
            float(cycle_booking["koc_paid_amount"].sum())
            if not cycle_booking.empty
            else 0.0
        )

        cycle_booking_net = max(
            cycle_booking_paid - cycle_koc_paid,
            0
        )

        cycle_total_revenue = (
            cycle_tap + cycle_booking_net
        )

        target_row = revenue_targets[
            revenue_targets["target_month"].astype(str).isin(
                cycle_months
            )
        ]

        saved_target = (
            float(target_row.iloc[0]["target_revenue"])
            if not target_row.empty
            else 0.0
        )

        saved_target_note = (
            str(target_row.iloc[0]["note"] or "")
            if not target_row.empty
            else ""
        )

        st.info(
            f"📅 Chu kỳ Target: **{cycle_label}** — "
            f"Tháng {cycle_start} và {cycle_end} dùng chung 1 Target."
        )

        t1, t2 = st.columns([2, 1])

        with t1:
            target_revenue_input = st.number_input(
                "🎯 Target tổng doanh thu cho 2 tháng",
                min_value=0.0,
                value=saved_target,
                step=1000000.0,
                format="%.0f",
                key=f"dashboard_target_revenue_{cycle_start}_{cycle_end}"
            )

        with t2:
            target_note = st.text_input(
                "Ghi chú",
                value=saved_target_note,
                key=f"dashboard_target_note_{cycle_start}_{cycle_end}"
            )

        if st.button(
            "💾 Lưu Target 2 tháng",
            type="primary",
            key=f"save_dashboard_target_{cycle_start}_{cycle_end}"
        ):

            for target_month in cycle_months:
                cursor.execute(
                    """
                    INSERT INTO total_revenue_targets
                    (
                        target_month,
                        target_revenue,
                        note
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(target_month)
                    DO UPDATE SET
                        target_revenue = excluded.target_revenue,
                        note = excluded.note
                    """,
                    (
                        target_month,
                        float(target_revenue_input),
                        target_note.strip()
                    )
                )

            conn.commit()

            st.success(
                f"✅ Đã lưu chung Target {money(target_revenue_input)} "
                f"cho chu kỳ {cycle_label}."
            )

            st.rerun()

        target_revenue = float(target_revenue_input)

        if target_revenue > 0:
            achievement_rate = (
                cycle_total_revenue
                / target_revenue
                * 100
            )

            remaining_revenue = max(
                target_revenue - cycle_total_revenue,
                0
            )

            excess_revenue = max(
                cycle_total_revenue - target_revenue,
                0
            )
        else:
            achievement_rate = 0
            remaining_revenue = 0
            excess_revenue = 0

        q1, q2, q3 = st.columns(3)

        with q1:
            st.metric(
                "🎯 Target 2 tháng",
                money(target_revenue)
            )

        with q2:
            st.metric(
                "💰 Doanh thu 2 tháng",
                money(cycle_total_revenue)
            )

        with q3:
            st.metric(
                "📊 % đạt Target",
                percent(achievement_rate)
            )

        if target_revenue > 0:
            if cycle_total_revenue >= target_revenue:
                st.success(
                    f"🎉 Chu kỳ {cycle_label} đã đạt Target! "
                    f"Vượt {money(excess_revenue)}."
                )
            else:
                st.warning(
                    f"📌 Chu kỳ {cycle_label} còn thiếu "
                    f"{money(remaining_revenue)} doanh thu để đạt Target."
                )

        st.caption(
            "Doanh thu 2 tháng = Hoa hồng TAP thực tế + Gói dịch vụ ròng "
            "của cả 2 tháng trong chu kỳ."
        )

        if not current.empty:

            st.divider()
            st.subheader("🎯 Hiệu quả Brand")

            brand_actual = (
                current.groupby("store_name", as_index=False)
                .agg(
                    GMV=("gmv", "sum"),
                    AC=("ac", "sum"),
                    KOC=("creator_name", "nunique")
                )
            )

            brand_master = pd.read_sql(
                """
                SELECT brand_name, commission, target_gmv
                FROM brands
                """,
                conn
            )

            brand_master["brand_name"] = (
                brand_master["brand_name"]
                .fillna("")
                .astype(str)
                .str.replace("\r", "", regex=False)
                .str.strip()
            )

            brand_actual["store_name"] = (
                brand_actual["store_name"]
                .fillna("")
                .astype(str)
                .str.replace("\r", "", regex=False)
                .str.strip()
            )

            brand_perf = brand_actual.merge(
                brand_master,
                left_on="store_name",
                right_on="brand_name",
                how="left"
            )

            brand_perf["target_gmv"] = (
                pd.to_numeric(
                    brand_perf["target_gmv"],
                    errors="coerce"
                )
                .fillna(0)
            )

            brand_perf["% hoàn thành"] = 0.0
            has_target = brand_perf["target_gmv"] > 0

            brand_perf.loc[
                has_target,
                "% hoàn thành"
            ] = (
                brand_perf.loc[has_target, "GMV"]
                / brand_perf.loc[has_target, "target_gmv"]
                * 100
            )

            brand_perf["Tỷ lệ hoa hồng"] = (
                brand_perf["AC"]
                / brand_perf["GMV"]
                * 100
            ).fillna(0)

            brand_perf = brand_perf.sort_values(
                "AC",
                ascending=False
            )

            below_target = brand_perf[
                (brand_perf["target_gmv"] > 0)
                & (brand_perf["% hoàn thành"] < 100)
            ]

            if not below_target.empty:
                st.warning(
                    f"⚠️ Có {len(below_target):,} Brand chưa đạt 100% GMV mục tiêu."
                )
            else:
                st.success(
                    "✅ Tất cả Brand có target đều đã đạt GMV mục tiêu."
                )

            brand_display = brand_perf[
                [
                    "store_name",
                    "GMV",
                    "target_gmv",
                    "% hoàn thành",
                    "AC",
                    "Tỷ lệ hoa hồng",
                    "KOC"
                ]
            ].copy()

            brand_display.columns = [
                "Brand",
                "GMV",
                "GMV mục tiêu",
                "% hoàn thành",
                "Hoa hồng thực tế",
                "Tỷ lệ hoa hồng",
                "KOC"
            ]

            brand_display["GMV"] = brand_display["GMV"].apply(money)

            brand_display["GMV mục tiêu"] = (
                brand_display["GMV mục tiêu"]
                .apply(lambda x: money(x) if x > 0 else "—")
            )

            brand_display["% hoàn thành"] = (
                brand_display["% hoàn thành"]
                .apply(lambda x: f"{x:.1f}%")
            )

            brand_display["Hoa hồng thực tế"] = (
                brand_display["Hoa hồng thực tế"].apply(money)
            )

            brand_display["Tỷ lệ hoa hồng"] = (
                brand_display["Tỷ lệ hoa hồng"].apply(percent)
            )

            st.dataframe(
                brand_display,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            left, right = st.columns(2)

            with left:
                st.subheader("🏆 Top 10 Brand")

                top_brand = (
                    current.groupby("store_name", as_index=False)
                    .agg(
                        GMV=("gmv", "sum"),
                        AC=("ac", "sum")
                    )
                    .sort_values("AC", ascending=False)
                    .head(10)
                )

                top_brand_display = top_brand.copy()
                top_brand_display["GMV"] = top_brand_display["GMV"].apply(money)
                top_brand_display["AC"] = top_brand_display["AC"].apply(money)
                top_brand_display.columns = [
                    "Brand",
                    "GMV",
                    "Hoa hồng thực tế"
                ]

                st.dataframe(
                    top_brand_display,
                    use_container_width=True,
                    hide_index=True
                )

            with right:
                st.subheader("👑 Top 10 KOC/NST")

                top_koc = (
                    current.groupby("creator_name", as_index=False)
                    .agg(
                        GMV=("gmv", "sum"),
                        AC=("ac", "sum")
                    )
                    .sort_values("AC", ascending=False)
                    .head(10)
                )

                top_koc_display = top_koc.copy()
                top_koc_display["GMV"] = top_koc_display["GMV"].apply(money)
                top_koc_display["AC"] = top_koc_display["AC"].apply(money)
                top_koc_display.columns = [
                    "KOC/NST",
                    "GMV",
                    "Hoa hồng thực tế"
                ]

                st.dataframe(
                    top_koc_display,
                    use_container_width=True,
                    hide_index=True
                )

        if not current_booking.empty:

            st.divider()
            st.subheader("📦 Booking Service tháng")

            booking_summary = (
                current_booking.groupby(
                    "brand_name",
                    as_index=False
                )
                .agg(
                    Hợp_đồng=("contract_fee", "sum"),
                    Đã_thanh_toán=("paid_amount", "sum"),
                    KOC_đã_thanh_toán=("koc_paid_amount", "sum"),
                    Đang_chạy=("running", "sum")
                )
                .sort_values(
                    "Đã_thanh_toán",
                    ascending=False
                )
            )

            booking_summary["Chưa_thanh_toán"] = (
                booking_summary["Hợp_đồng"]
                - booking_summary["Đã_thanh_toán"]
            ).clip(lower=0)

            booking_summary_display = booking_summary.copy()
            booking_summary_display.columns = [
                "Brand",
                "Tổng hợp đồng",
                "Đã thanh toán",
                "Đang chạy",
                "Chưa thanh toán"
            ]

            for col in [
                "Tổng hợp đồng",
                "Đã thanh toán",
                "Chưa thanh toán"
            ]:
                booking_summary_display[col] = (
                    booking_summary_display[col].apply(money)
                )

            st.dataframe(
                booking_summary_display,
                use_container_width=True,
                hide_index=True
            )

        st.divider()
        st.subheader("📊 Cơ cấu doanh thu tháng")

        revenue_chart = pd.DataFrame(
            {
                "Doanh thu": [
                    current_ac,
                    booking_net_revenue
                ]
            },
            index=[
                "Hoa hồng TAP",
                "Gói dịch vụ"
            ]
        )

        st.bar_chart(
            revenue_chart,
            height=360
        )

        st.caption(
            f"Tháng {selected_month}: "
            f"Hoa hồng TAP {money(current_ac)} • "
            f"Gói dịch vụ ròng {money(booking_net_revenue)}"
        )

        st.divider()
        st.subheader("📅 Tổng quan các tháng")

        monthly_summary = (
            analytics_all.groupby(
                "report_month",
                as_index=False
            )
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum"),
                KOC=("creator_name", "nunique"),
                Brand=("store_name", "nunique")
            )
            if not analytics_all.empty
            else pd.DataFrame(
                columns=[
                    "report_month",
                    "GMV",
                    "AC",
                    "KOC",
                    "Brand"
                ]
            )
        )

        booking_month_summary = (
            booking_all.assign(
                Booking_net=(
                    booking_all["paid_amount"]
                    - booking_all["koc_paid_amount"]
                ).clip(lower=0)
            )
            .groupby(
                "contract_month",
                as_index=False
            )
            .agg(
                Booking=("paid_amount", "sum"),
                KOC_paid=("koc_paid_amount", "sum"),
                Booking_net=("Booking_net", "sum")
            )
            .rename(
                columns={
                    "contract_month": "report_month"
                }
            )
            if not booking_all.empty
            else pd.DataFrame(
                columns=[
                    "report_month",
                    "Booking",
                    "KOC_paid",
                    "Booking_net"
                ]
            )
        )

        monthly_summary = monthly_summary.merge(
            booking_month_summary,
            on="report_month",
            how="outer"
        )

        revenue_target_summary = revenue_targets[
            [
                "target_month",
                "target_revenue"
            ]
        ].copy()

        revenue_target_summary = revenue_target_summary.rename(
            columns={
                "target_month": "report_month",
                "target_revenue": "Revenue_Target"
            }
        )

        monthly_summary = monthly_summary.merge(
            revenue_target_summary,
            on="report_month",
            how="outer"
        )

        for col in [
            "GMV",
            "AC",
            "KOC",
            "Brand",
            "Booking",
            "KOC_paid",
            "Booking_net",
            "Revenue_Target"
        ]:
            if col not in monthly_summary.columns:
                monthly_summary[col] = 0

            monthly_summary[col] = (
                pd.to_numeric(
                    monthly_summary[col],
                    errors="coerce"
                )
                .fillna(0)
            )

        monthly_summary["Tổng doanh thu"] = (
            monthly_summary["AC"]
            + monthly_summary["Booking_net"]
        )

        monthly_summary["% đạt Target"] = 0.0

        has_revenue_target = (
            monthly_summary["Revenue_Target"] > 0
        )

        monthly_summary.loc[
            has_revenue_target,
            "% đạt Target"
        ] = (
            monthly_summary.loc[
                has_revenue_target,
                "Tổng doanh thu"
            ]
            / monthly_summary.loc[
                has_revenue_target,
                "Revenue_Target"
            ]
            * 100
        )

        monthly_summary["Tỷ lệ hoa hồng"] = (
            monthly_summary["AC"]
            / monthly_summary["GMV"]
            * 100
        ).fillna(0)

        monthly_summary = monthly_summary.sort_values(
            "report_month",
            ascending=False
        )

        monthly_display = monthly_summary[
            [
                "report_month",
                "GMV",
                "AC",
                "Booking",
                "KOC_paid",
                "Booking_net",
                "Tổng doanh thu",
                "Revenue_Target",
                "% đạt Target",
                "KOC",
                "Brand",
                "Tỷ lệ hoa hồng"
            ]
        ].copy()

        monthly_display.columns = [
            "Tháng",
            "GMV",
            "Hoa hồng thực tế",
            "Booking đã thanh toán",
            "KOC đã thanh toán",
            "Doanh thu Booking ròng",
            "Tổng doanh thu",
            "Target doanh thu",
            "% đạt Target",
            "KOC",
            "Brand",
            "Tỷ lệ hoa hồng"
        ]

        for col in [
            "GMV",
            "Hoa hồng thực tế",
            "Booking đã thanh toán",
            "KOC đã thanh toán",
            "Doanh thu Booking ròng",
            "Tổng doanh thu",
            "Target doanh thu"
        ]:
            monthly_display[col] = monthly_display[col].apply(money)

        monthly_display["% đạt Target"] = (
            monthly_display["% đạt Target"].apply(percent)
        )

        monthly_display["Tỷ lệ hoa hồng"] = (
            monthly_display["Tỷ lệ hoa hồng"].apply(percent)
        )

        st.dataframe(
            monthly_display,
            use_container_width=True,
            hide_index=True
        )


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

elif page == "🎯 TAP Target":

    st.header("🎯 TAP Target Management")
    st.write(
        "Theo dõi Target hoa hồng TAP theo tháng và đối chiếu "
        "với hoa hồng thực tế từ dữ liệu TikTok."
    )

    analytics_target_data = pd.read_sql(
        """
        SELECT
            report_month,
            creator_name,
            store_name,
            gmv,
            ac
        FROM analytics
        """,
        conn
    )

    if analytics_target_data.empty:

        st.info(
            "📌 Chưa có dữ liệu TikTok. "
            "Hãy vào **📊 Monthly Analytics** để upload báo cáo trước."
        )

    else:

        target_months = sorted(
            analytics_target_data["report_month"]
            .dropna()
            .unique()
            .tolist(),
            reverse=True
        )

        selected_target_month = st.selectbox(
            "📅 Tháng cần theo dõi",
            target_months,
            key="tap_target_month"
        )

        month_actual = analytics_target_data[
            analytics_target_data["report_month"] == selected_target_month
        ].copy()

        actual_ac = float(month_actual["ac"].sum())
        actual_gmv = float(month_actual["gmv"].sum())

        actual_rate = (
            actual_ac / actual_gmv * 100
            if actual_gmv != 0
            else 0
        )

        target_row = cursor.execute(
            """
            SELECT target_ac, note
            FROM tap_targets
            WHERE target_month = ?
            """,
            (selected_target_month,)
        ).fetchone()

        saved_target = float(target_row[0]) if target_row else 0.0
        saved_note = str(target_row[1]) if target_row and target_row[1] else ""

        st.divider()
        st.subheader("🎯 Đặt Target TAP")

        target_input = st.number_input(
            "Target hoa hồng TAP",
            min_value=0.0,
            value=saved_target,
            step=500000.0,
            format="%.0f",
            key=f"target_input_{selected_target_month}"
        )

        target_note = st.text_area(
            "Ghi chú Target",
            value=saved_note,
            placeholder="Ví dụ: Target tháng theo kế hoạch team TAP",
            key=f"target_note_{selected_target_month}"
        )

        if st.button(
            "💾 Lưu Target",
            type="primary",
            key=f"save_target_{selected_target_month}"
        ):

            cursor.execute(
                """
                INSERT INTO tap_targets (target_month, target_ac, note)
                VALUES (?, ?, ?)
                ON CONFLICT(target_month)
                DO UPDATE SET
                    target_ac = excluded.target_ac,
                    note = excluded.note
                """,
                (
                    selected_target_month,
                    float(target_input),
                    target_note.strip()
                )
            )

            conn.commit()

            st.success(
                f"✅ Đã lưu Target {selected_target_month}: "
                f"{money(target_input)}"
            )

            st.rerun()

        target_value = float(target_input)

        if target_value > 0:
            achievement = actual_ac / target_value * 100
            remaining = max(target_value - actual_ac, 0)
            over_target = max(actual_ac - target_value, 0)
        else:
            achievement = 0
            remaining = 0
            over_target = 0

        st.divider()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("🎯 Target", money(target_value))

        with col2:
            st.metric("💵 Hoa hồng thực tế", money(actual_ac))

        with col3:
            st.metric("📊 % đạt Target", percent(achievement))

        with col4:
            if target_value > 0 and remaining > 0:
                st.metric("⚠️ Còn thiếu", money(remaining))
            elif target_value > 0:
                st.metric("✅ Vượt Target", money(over_target))
            else:
                st.metric("⚠️ Còn thiếu", "—")

        if target_value <= 0:
            st.info("💡 Chưa đặt Target cho tháng này.")
        elif actual_ac >= target_value:
            st.success(
                f"🎉 Tháng {selected_target_month} đã đạt Target TAP!"
            )
        else:
            st.warning(
                f"📌 Cần thêm {money(remaining)} hoa hồng thực tế để đạt Target."
            )

        st.subheader("🧮 Ước tính GMV cần thêm")

        if target_value > 0 and remaining > 0 and actual_rate > 0:

            extra_gmv = remaining / (actual_rate / 100)

            c1, c2 = st.columns(2)

            with c1:
                st.metric("GMV hiện tại", money(actual_gmv))

            with c2:
                st.metric("GMV cần thêm (ước tính)", money(extra_gmv))

            st.caption(
                "Ước tính theo tỷ lệ hoa hồng thực tế hiện tại "
                f"({actual_rate:.4f}%)."
            )

        elif target_value > 0 and remaining > 0:
            st.info(
                "Chưa thể ước tính GMV cần thêm vì tỷ lệ hoa hồng hiện tại bằng 0%."
            )

        st.divider()
        st.subheader("🏷️ Đóng góp của từng Brand")

        brand_target = (
            month_actual.groupby("store_name", as_index=False)
            .agg(
                GMV=("gmv", "sum"),
                AC=("ac", "sum"),
                KOC=("creator_name", "nunique")
            )
            .sort_values("AC", ascending=False)
        )

        brand_target["Đóng góp hoa hồng (%)"] = (
            brand_target["AC"] / actual_ac * 100
            if actual_ac > 0
            else 0
        )

        brand_target["Đóng góp vào Target"] = (
            brand_target["AC"] / target_value * 100
            if target_value > 0
            else 0
        )

        brand_target_display = brand_target.copy()
        brand_target_display.columns = [
            "Brand",
            "GMV",
            "Hoa hồng thực tế",
            "KOC",
            "Đóng góp hoa hồng (%)",
            "Đóng góp vào Target"
        ]

        brand_target_display["GMV"] = (
            brand_target_display["GMV"].apply(money)
        )
        brand_target_display["Hoa hồng thực tế"] = (
            brand_target_display["Hoa hồng thực tế"].apply(money)
        )
        brand_target_display["Đóng góp hoa hồng (%)"] = (
            brand_target_display["Đóng góp hoa hồng (%)"].apply(percent)
        )
        brand_target_display["Đóng góp vào Target"] = (
            brand_target_display["Đóng góp vào Target"].apply(percent)
        )

        st.dataframe(
            brand_target_display,
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.subheader("📅 Lịch sử Target")

        target_history = pd.read_sql(
            """
            SELECT target_month, target_ac, note
            FROM tap_targets
            ORDER BY target_month DESC
            """,
            conn
        )

        if target_history.empty:
            st.info("Chưa có Target nào được lưu.")
        else:

            history_actual = (
                analytics_target_data.groupby(
                    "report_month",
                    as_index=False
                )["ac"]
                .sum()
                .rename(columns={"ac": "actual_ac"})
            )

            target_history = target_history.merge(
                history_actual,
                left_on="target_month",
                right_on="report_month",
                how="left"
            )

            target_history["actual_ac"] = (
                target_history["actual_ac"].fillna(0)
            )

            target_history["% đạt"] = 0.0

            valid_target = target_history["target_ac"] > 0

            target_history.loc[valid_target, "% đạt"] = (
                target_history.loc[valid_target, "actual_ac"]
                / target_history.loc[valid_target, "target_ac"]
                * 100
            )

            history_display = target_history[
                [
                    "target_month",
                    "target_ac",
                    "actual_ac",
                    "% đạt",
                    "note"
                ]
            ].copy()

            history_display.columns = [
                "Tháng",
                "Target",
                "Hoa hồng thực tế",
                "% đạt",
                "Ghi chú"
            ]

            history_display["Target"] = (
                history_display["Target"].apply(money)
            )
            history_display["Hoa hồng thực tế"] = (
                history_display["Hoa hồng thực tế"].apply(money)
            )
            history_display["% đạt"] = (
                history_display["% đạt"].apply(percent)
            )

            st.dataframe(
                history_display,
                use_container_width=True,
                hide_index=True
            )


elif page == "📦 Booking Service":

    st.header("📦 Booking Service")
    st.write(
        "Quản lý gói dịch vụ Booking theo tháng, tình trạng chạy "
        "và số tiền đã thanh toán."
    )

    package_prices = {
        "TikTok/FBIG - Massive KOC": {
            "B1": {"STANDARD": 5000000, "SILVER": 7000000, "GOLD": 10000000},
            "C1": {"STANDARD": 32400000, "SILVER": 48000000, "GOLD": 90000000},
            "C2": {"STANDARD": 86400000, "SILVER": 132000000, "GOLD": 258000000},
            "C3": {"STANDARD": 118800000, "SILVER": 192000000, "GOLD": 360000000},
            "C4": {"STANDARD": 69600000, "SILVER": 198000000, "GOLD": 300000000},
            "P5": {"STANDARD": 43200000, "SILVER": 69000000, "GOLD": 120000000},
            "P6": {"STANDARD": 97200000, "SILVER": 138000000, "GOLD": 252000000},
            "P7": {"STANDARD": 57600000, "SILVER": 90000000, "GOLD": 168000000}
        },
        "TikTok/FBIG - Livestream": {
            "Op 1": {"STANDARD": 21600000, "SILVER": 33000000, "GOLD": 60000000},
            "Op 2": {"STANDARD": 36000000, "SILVER": 57000000, "GOLD": 108000000},
            "Op 3": {"STANDARD": 57600000, "SILVER": 90000000, "GOLD": 168000000}
        },
        "Threads": {
            "R1": {"STANDARD": 21600000, "SILVER": 33000000, "GOLD": 62400000},
            "R2": {"STANDARD": 36000000, "SILVER": 57000000, "GOLD": 108000000}
        }
    }

    service_groups = list(package_prices.keys())

    # =====================================================
    # THÊM BOOKING
    # =====================================================

    with st.expander("➕ Thêm Booking", expanded=True):

        with st.form("booking_add_form"):

            left, right = st.columns(2)

            with left:

                booking_month_date = st.date_input(
                    "📅 Tháng hợp đồng",
                    value=date.today().replace(day=1)
                )

                booking_month = booking_month_date.strftime("%Y-%m")

                brand_list = (
                    pd.read_sql(
                        "SELECT brand_name FROM brands ORDER BY brand_name",
                        conn
                    )["brand_name"]
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                brand_options = ["➕ Brand khác"] + brand_list

                brand_choice = st.selectbox(
                    "🏷️ Brand",
                    brand_options
                )

                if brand_choice == "➕ Brand khác":
                    brand_name_input = st.text_input("Tên Brand")
                else:
                    brand_name_input = brand_choice

                service_group = st.selectbox(
                    "📦 Nhóm dịch vụ",
                    service_groups
                )

            with right:

                package_name = st.selectbox(
                    "Gói dịch vụ",
                    list(package_prices[service_group].keys())
                )

                tier = st.selectbox(
                    "Tier",
                    ["STANDARD", "SILVER", "GOLD"]
                )

                default_fee = (
                    package_prices[service_group][package_name][tier]
                )

                contract_fee = st.number_input(
                    "💰 Giá hợp đồng",
                    min_value=0.0,
                    value=float(default_fee),
                    step=500000.0,
                    format="%.0f"
                )

                st.caption(
                    f"Giá gợi ý theo package: {money(default_fee)}"
                )

                running = st.checkbox("🟢 Đang chạy")

                paid = st.checkbox("✅ Đã thanh toán")

                paid_amount = st.number_input(
                    "💵 Tiền Brand đã thanh toán",
                    min_value=0.0,
                    value=float(contract_fee) if paid else 0.0,
                    step=500000.0,
                    format="%.0f"
                )

                koc_paid_amount = st.number_input(
                    "👤 Tiền KOC đã thanh toán",
                    min_value=0.0,
                    value=0.0,
                    step=100000.0,
                    format="%.0f"
                )

                st.caption(
                    "Doanh thu Booking ròng = Brand đã thanh toán - KOC đã thanh toán."
                )

                note = st.text_area("Ghi chú")

            submit_booking = st.form_submit_button(
                "💾 Lưu Booking",
                type="primary"
            )

        if submit_booking:

            if not str(brand_name_input).strip():

                st.error("Vui lòng nhập Brand.")

            else:

                paid_amount_final = (
                    min(
                        float(paid_amount),
                        float(contract_fee)
                    )
                    if paid
                    else 0.0
                )

                cursor.execute(
                    """
                    INSERT INTO booking_services
                    (
                        contract_month,
                        brand_name,
                        service_group,
                        package_name,
                        tier,
                        contract_fee,
                        running,
                        paid,
                        paid_amount,
                        koc_paid_amount,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        booking_month,
                        brand_name_input.strip(),
                        service_group,
                        package_name,
                        tier,
                        float(contract_fee),
                        1 if running else 0,
                        1 if paid else 0,
                        paid_amount_final,
                        min(
                            float(koc_paid_amount),
                            float(contract_fee)
                        ),
                        note.strip()
                    )
                )

                conn.commit()

                st.success("✅ Đã thêm Booking Service.")
                st.rerun()

    # =====================================================
    # DANH SÁCH + CHỈNH NHANH
    # =====================================================

    st.divider()
    st.subheader("📋 Quản lý Booking")

    booking_df = pd.read_sql(
        """
        SELECT
            id,
            contract_month,
            brand_name,
            service_group,
            package_name,
            tier,
            contract_fee,
            running,
            paid,
            paid_amount,
            koc_paid_amount,
            note
        FROM booking_services
        ORDER BY contract_month DESC, id DESC
        """,
        conn
    )

    if booking_df.empty:

        st.info("Chưa có Booking nào.")

    else:

        filter_months = sorted(
            booking_df["contract_month"]
            .dropna()
            .astype(str)
            .unique()
            .tolist(),
            reverse=True
        )

        f1, f2, f3 = st.columns(3)

        with f1:
            booking_filter_month = st.selectbox(
                "📅 Lọc theo tháng",
                ["Tất cả"] + filter_months,
                key="booking_filter_month"
            )

        with f2:
            booking_filter_status = st.selectbox(
                "🔎 Trạng thái",
                [
                    "Tất cả",
                    "🟢 Đang chạy",
                    "⏳ Chưa chạy",
                    "✅ Đã thanh toán",
                    "⏳ Chưa thanh toán"
                ],
                key="booking_filter_status"
            )

        with f3:
            booking_search = st.text_input(
                "🔎 Tìm Brand / Gói",
                key="booking_search"
            )

        filtered_booking = booking_df.copy()

        if booking_filter_month != "Tất cả":
            filtered_booking = filtered_booking[
                filtered_booking["contract_month"].astype(str)
                == booking_filter_month
            ]

        if booking_filter_status == "🟢 Đang chạy":
            filtered_booking = filtered_booking[
                filtered_booking["running"] == 1
            ]
        elif booking_filter_status == "⏳ Chưa chạy":
            filtered_booking = filtered_booking[
                filtered_booking["running"] == 0
            ]
        elif booking_filter_status == "✅ Đã thanh toán":
            filtered_booking = filtered_booking[
                filtered_booking["paid"] == 1
            ]
        elif booking_filter_status == "⏳ Chưa thanh toán":
            filtered_booking = filtered_booking[
                filtered_booking["paid"] == 0
            ]

        if booking_search.strip():
            q = booking_search.strip().lower()

            filtered_booking = filtered_booking[
                filtered_booking["brand_name"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
                |
                filtered_booking["package_name"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
                |
                filtered_booking["service_group"]
                .astype(str)
                .str.lower()
                .str.contains(q, na=False)
            ]

        total_contract = float(
            filtered_booking["contract_fee"].sum()
        )

        total_paid = float(
            filtered_booking["paid_amount"].sum()
        )

        total_koc_paid = float(
            filtered_booking["koc_paid_amount"].sum()
        )

        total_booking_net = (
            total_paid - total_koc_paid
        )

        total_running = float(
            filtered_booking.loc[
                filtered_booking["running"] == 1,
                "contract_fee"
            ].sum()
        )

        total_unpaid = max(
            total_contract - total_paid,
            0
        )

        k1, k2, k3, k4, k5 = st.columns(5)

        with k1:
            st.metric(
                "📦 Tổng hợp đồng",
                money(total_contract)
            )

        with k2:
            st.metric(
                "🟢 Đang chạy",
                money(total_running)
            )

        with k3:
            st.metric(
                "✅ Brand đã thanh toán",
                money(total_paid)
            )

        with k4:
            st.metric(
                "👤 KOC đã thanh toán",
                money(total_koc_paid)
            )

        with k5:
            st.metric(
                "💰 Doanh thu Booking ròng",
                money(total_booking_net)
            )

        # Bảng chỉnh trực tiếp.
        editor_source = filtered_booking[
            [
                "id",
                "contract_month",
                "brand_name",
                "service_group",
                "package_name",
                "tier",
                "contract_fee",
                "running",
                "paid",
                "paid_amount",
                "koc_paid_amount",
                "note"
            ]
        ].copy()

        editor_source["running"] = (
            editor_source["running"].astype(bool)
        )

        editor_source["paid"] = (
            editor_source["paid"].astype(bool)
        )

        edited_booking = st.data_editor(
            editor_source,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="booking_editor",
            column_config={
                "id": st.column_config.NumberColumn(
                    "ID",
                    disabled=True
                ),
                "contract_month": st.column_config.TextColumn(
                    "Tháng",
                    disabled=True
                ),
                "brand_name": st.column_config.TextColumn(
                    "Brand",
                    disabled=True
                ),
                "service_group": st.column_config.TextColumn(
                    "Nhóm dịch vụ",
                    disabled=True
                ),
                "package_name": st.column_config.TextColumn(
                    "Gói",
                    disabled=True
                ),
                "tier": st.column_config.TextColumn(
                    "Tier",
                    disabled=True
                ),
                "contract_fee": st.column_config.NumberColumn(
                    "Giá hợp đồng",
                    format="%,.0f",
                    disabled=True
                ),
                "running": st.column_config.CheckboxColumn(
                    "🟢 Đang chạy"
                ),
                "paid": st.column_config.CheckboxColumn(
                    "✅ Đã thanh toán"
                ),
                "paid_amount": st.column_config.NumberColumn(
                    "💵 Brand đã thanh toán",
                    min_value=0,
                    format="%,.0f"
                ),
                "koc_paid_amount": st.column_config.NumberColumn(
                    "👤 KOC đã thanh toán",
                    min_value=0,
                    format="%,.0f"
                ),
                "note": st.column_config.TextColumn(
                    "Ghi chú"
                )
            },
            disabled=[
                "id",
                "contract_month",
                "brand_name",
                "service_group",
                "package_name",
                "tier",
                "contract_fee"
            ]
        )

        st.caption(
            "💡 Tick trực tiếp Đang chạy/Đã thanh toán hoặc sửa số tiền ngay trên bảng."
        )

        if st.button(
            "💾 Lưu tất cả thay đổi",
            type="primary",
            key="save_booking_edits"
        ):

            updated_count = 0

            for _, row in edited_booking.iterrows():

                booking_id = int(row["id"])

                original_row = filtered_booking[
                    filtered_booking["id"] == booking_id
                ]

                if original_row.empty:
                    continue

                original_row = original_row.iloc[0]

                running_value = bool(row["running"])
                paid_value = bool(row["paid"])

                contract_value = float(
                    original_row["contract_fee"]
                )

                paid_value_amount = max(
                    0.0,
                    min(
                        float(row["paid_amount"]),
                        contract_value
                    )
                )

                koc_value_amount = max(
                    0.0,
                    min(
                        float(row["koc_paid_amount"]),
                        contract_value
                    )
                )

                note_value = str(
                    row["note"]
                    if pd.notna(row["note"])
                    else ""
                )

                changed = (
                    running_value != bool(original_row["running"])
                    or paid_value != bool(original_row["paid"])
                    or paid_value_amount != float(original_row["paid_amount"])
                    or koc_value_amount != float(original_row["koc_paid_amount"])
                    or note_value != str(original_row["note"] or "")
                )

                if changed:

                    cursor.execute(
                        """
                        UPDATE booking_services
                        SET
                            running = ?,
                            paid = ?,
                            paid_amount = ?,
                            koc_paid_amount = ?,
                            note = ?
                        WHERE id = ?
                        """,
                        (
                            1 if running_value else 0,
                            1 if paid_value else 0,
                            paid_value_amount if paid_value else 0.0,
                            koc_value_amount,
                            note_value.strip(),
                            booking_id
                        )
                    )

                    updated_count += 1

            conn.commit()

            st.success(
                f"✅ Đã lưu {updated_count} Booking."
            )

            st.rerun()

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
            # LOẠI CASE CÓ GMV NHƯNG KHÔNG CÓ HOA HỒNG THỰC TẾ
            # -------------------------------------------------
            # Chỉ tính các case có cả GMV và hoa hồng thực tế.
            # Case có GMV > 0 nhưng AC <= 0 sẽ bị loại khỏi:
            # Tổng GMV, tổng hoa hồng và các bảng Top.
            # -------------------------------------------------
            before_filter = len(raw)

            raw = raw[
                (raw["gmv"] > 0)
                & (raw["ac"] > 0)
            ].copy()

            excluded_cases = before_filter - len(raw)

            if excluded_cases > 0:
                st.info(
                    f"ℹ️ Đã tự động loại {excluded_cases:,} case "
                    f"có GMV nhưng không có hoa hồng thực tế."
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
                "AC",
                ascending=False
            )
            .head(20)
        )


        top_brand["Tỷ lệ hoa hồng"] = (
            top_brand["AC"]
            / top_brand["GMV"]
            * 100
        ).fillna(0)


        brand_display = top_brand.copy()


        brand_display["GMV"] = (
            brand_display["GMV"]
            .apply(money)
        )


        brand_display["Hoa hồng thực tế"] = (
            brand_display["AC"]
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
                "AC",
                ascending=False
            )
            .head(20)
        )


        top_koc["Tỷ lệ hoa hồng"] = (
            top_koc["AC"]
            / top_koc["GMV"]
            * 100
        ).fillna(0)


        koc_display = top_koc.copy()


        koc_display["GMV"] = (
            koc_display["GMV"]
            .apply(money)
        )


        koc_display["Hoa hồng thực tế"] = (
            koc_display["AC"]
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


        analysis_display = (
            brand_analysis.copy()
        )


        analysis_display["GMV"] = (
            analysis_display["GMV"]
            .apply(money)
        )


        analysis_display["Hoa hồng thực tế"] = (
            analysis_display["AC"]
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
            monthly["AC"]
            / monthly["GMV"]
            * 100
        ).fillna(0)


        monthly_display = monthly.copy()


        monthly_display["GMV"] = (
            monthly_display["GMV"]
            .apply(money)
        )


        monthly_display["Hoa hồng thực tế"] = (
            monthly_display["AC"]
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
