import streamlit as st

st.set_page_config(
    page_title="KOC Management",
    page_icon="📊",
    layout="wide"
)

st.title("📊 KOC Management & Analytics")
st.write("Hệ thống quản lý KOC/KOL và phân tích dữ liệu")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Tổng KOC", 0)

with col2:
    st.metric("Tổng Brand", 0)

with col3:
    st.metric("Tổng GMV", "0 VNĐ")

st.success("🚀 Web đang được khởi tạo!")
