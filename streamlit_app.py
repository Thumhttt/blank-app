import sqlite3
from datetime import datetime
import pandas as pd  # DataFrame operations

# Kiểm tra Streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
    # Thiết lập cấu hình trang ngay sau khi import Streamlit
    st.set_page_config(page_title="Khoa Giám Sát Cảnh Báo - Quản Lý Đào Tạo", layout="wide")
except ModuleNotFoundError:
    STREAMLIT_AVAILABLE = False

# --------------------
# Database utilities
# --------------------
def init_db(db_path='training.db'):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    # Tạo bảng courses
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date_created TEXT NOT NULL
        )
    """)
    # Migration courses: thêm các cột mới nếu chưa có
    c.execute("PRAGMA table_info(courses)")
    cols = [row[1] for row in c.fetchall()]
    for col, ddl in [
        ('duration_type', "ALTER TABLE courses ADD COLUMN duration_type TEXT NOT NULL DEFAULT 'Dài hạn'"),
        ('start_date',    "ALTER TABLE courses ADD COLUMN start_date TEXT"),
        ('end_date',      "ALTER TABLE courses ADD COLUMN end_date TEXT"),
        ('image_url',     "ALTER TABLE courses ADD COLUMN image_url TEXT"),
    ]:
        if col not in cols:
            c.execute(ddl)
    # Tạo bảng participants
    c.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            date_created TEXT NOT NULL
        )
    """)
    # Migration participants
    c.execute("PRAGMA table_info(participants)")
    cols = [row[1] for row in c.fetchall()]
    for col, ddl in [
        ('phone', "ALTER TABLE participants ADD COLUMN phone TEXT"),
        ('dob',   "ALTER TABLE participants ADD COLUMN dob TEXT"),
    ]:
        if col not in cols:
            c.execute(ddl)
    # Tạo bảng enrollments
    c.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            participant_id INTEGER,
            date_enrolled TEXT NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    """)
    conn.commit()
    return conn


def get_df(query, params=()):
    return pd.read_sql_query(query, conn, params=params)


def run_app():
    if not STREAMLIT_AVAILABLE:
        print("Streamlit không có sẵn. Vui lòng cài đặt streamlit để chạy GUI.")
        return

    # Chèn CSS để tuỳ chỉnh giao diện
    st.markdown(
        '''
        <style>
            body { background-color: #0E1117; color: #FFFFFF; }
            h1 { color: #FF4B4B; text-align: center; }
            .stButton>button { background-color: #FF4B4B; color: white; border-radius: 8px; }
            .card { background: #1f1f23; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        </style>
        ''', unsafe_allow_html=True
    )
    st.title("Khoa Giám Sát Cảnh Báo - Quản Lý Đào Tạo")

    section = st.sidebar.radio(
        "Chọn mục:",
        ["Dashboard", "Thông tin Khóa học", "Quản lý Khóa học", "Thành viên", "Đăng ký"]
    )

    if section == "Dashboard":
        st.header("Dashboard")
        dash_type = st.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"])
        df_trend = get_df(
            """
            SELECT DATE(date_enrolled) AS Ngày, COUNT(*) AS Số_lượng
            FROM enrollments e
            JOIN courses c ON e.course_id=c.id
            WHERE c.duration_type=?
            GROUP BY DATE(date_enrolled)
            ORDER BY Ngày
            """, (dash_type,)
        )
        if not df_trend.empty:
            df_trend['Ngày'] = pd.to_datetime(df_trend['Ngày'])
            df_trend = df_trend.set_index('Ngày')
            st.subheader("Xu hướng đăng ký theo thời gian")
            st.line_chart(df_trend['Số_lượng'])

    elif section == "Thông tin Khóa học":
        st.header("Thông tin Khóa học")
        info_type = st.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"])
        df_info = get_df(
            """
            SELECT c.id AS Mã, c.title AS Tiêu_đề, c.duration_type AS Loại,
                   c.start_date AS 'Ngày bắt đầu', c.end_date AS 'Ngày kết thúc',
                   c.description AS 'Mô tả', c.image_url AS 'Hình ảnh'
            FROM courses c
            WHERE c.duration_type=?
            ORDER BY c.start_date
            """, (info_type,)
        )
        st.dataframe(df_info)
        st.subheader(f"Chi tiết trực quan khóa học ({info_type})")
        for _, row in df_info.iterrows():
            st.markdown(f"### {row['Tiêu_đề']}")
            cols = st.columns([1, 2])
            if row['Hình ảnh']:
                cols[0].image(row['Hình ảnh'], use_column_width=True)
            else:
                cols[0].write("_Chưa có hình ảnh_")
            cols[1].write(row['Mô tả'])
        df_ct = df_info.copy()
        df_ct['Ngày bắt đầu'] = pd.to_datetime(df_ct['Ngày bắt đầu'], errors='coerce')
        df_ct = df_ct.dropna(subset=['Ngày bắt đầu'])
        df_ct = df_ct.set_index('Ngày bắt đầu').resample('M').count()['Mã']
        st.line_chart(df_ct)

    elif section == "Quản lý Khóa học":
        st.header("Quản lý Khóa học")
        t1, t2 = st.tabs(["Danh sách", "Thêm mới"])
        with t1:
            df = get_df(
                "SELECT id AS 'Mã', title AS 'Tiêu đề', duration_type AS 'Loại', start_date AS 'Ngày bắt đầu', end_date AS 'Ngày kết thúc', description AS 'Mô tả', date_created AS 'Ngày tạo', image_url AS 'Hình ảnh' FROM courses"
            )
            st.dataframe(df)
        with t2:
            st.subheader("Thêm khóa học mới")
            title = st.text_input("Tên khóa học")
            duration_type = st.selectbox("Loại khóa học:", ["Ngắn hạn", "Dài hạn", "Seminar"])
            start = st.date_input("Ngày bắt đầu")
            end = st.date_input("Ngày kết thúc")
            desc = st.text_area("Mô tả khóa học")
            image_url = st.text_input("URL hình ảnh khóa học")
            if st.button("Thêm Khóa học"):
                if not title.strip():
                    st.error("Tên khóa học không được để trống.")
                elif start > end:
                    st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    conn.execute(
                        "INSERT INTO courses(title, description, date_created, duration_type, start_date, end_date, image_url) VALUES(?,?,?,?,?,?,?)",
                        (title, desc, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration_type, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), image_url)
                    )
                    conn.commit()
                    st.success("Thêm khóa học thành công!")

    elif section == "Thành viên":
        st.header("Quản lý Thành viên")
        t1, t2 = st.tabs(["Danh sách", "Thêm mới"])
        with t1:
            df = get_df(
                "SELECT id AS 'Mã', name AS 'Thành viên', email AS 'Email', phone AS 'Số điện thoại', dob AS 'Ngày sinh' FROM participants"
            )
            st.dataframe(df)
        with t2:
            st.subheader("Thêm thành viên mới")
            name = st.text_input("Tên thành viên")
            email = st.text_input("Email thành viên")
            phone = st.text_input("SỐ ĐIỆN THOẠI")
            dob_input = st.text_input("Ngày sinh (dd/mm/yyyy)")
            if st.button("Thêm Thành viên"):
                if not name.strip() or not email.strip():
                    st.error("Tên và Email không được để trống.")
                else:
                    try:
                        dob = datetime.strptime(dob_input, "%d/%m/%Y").strftime("%d/%m/%Y")
                    except:
                        st.error("Ngày sinh không hợp lệ. Vui lòng nhập dd/mm/yyyy.")
                    else:
                        try:
                            conn.execute(
                                "INSERT INTO participants(name, email, date_created, phone, dob) VALUES(?,?,?,?,?)",
                                (name, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), phone, dob)
                            )
                            conn.commit()
                            st.success("Thêm thành viên thành công!")
                        except sqlite3.IntegrityError:
                            st.error("Email đã tồn tại.")

    else:
        st.header("Đăng ký Khóa học")
        reg_type = st.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"])
        courses = get_df("SELECT id, title FROM courses WHERE duration_type = ?", (reg_type,))
        members = get_df("SELECT id, name FROM participants")
        if courses.empty or members.empty:
            st.warning("Vui lòng thêm khóa học và thành viên trước.")
        else:
            course_id = st.selectbox(
                "Chọn khóa học", options=courses['id'], format_func=lambda x: courses[courses.id == x]['title'].values[0]
            )
            member_id = st.selectbox(
                "Chọn thành viên", options=members['id'], format_func=lambda x: members[members.id == x]['name'].values[0]
            )
            if st.button("Ghi danh"):
                conn.execute(
                    "INSERT INTO enrollments(course_id, participant_id, date_enrolled) VALUES(?,?,?)",
                    (course_id, member_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                st.success("Đăng ký thành công!")
        df = get_df(
            """
            SELECT e.id AS 'Mã', p.name AS 'Thành viên', c.title AS 'Khóa học', e.date_enrolled AS 'Ngày đăng ký'
            FROM enrollments e
            JOIN participants p ON e.participant_id = p.id
            JOIN courses c ON e.course_id = c.id
            """
        )
        st.dataframe(df)

# --------------------
# Tests
# --------------------
def run_tests():
    test_conn = init_db(":memory:")
    global conn
    conn = test_conn
    for tbl in ['courses', 'participants', 'enrollments']:
        df = get_df(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        assert not df.empty, f"Bảng {tbl} chưa tồn tại"
    sch_c = get_df("PRAGMA table_info(courses)")['name'].tolist()
    for col in ['duration_type', 'start_date', 'end_date', 'image_url']:
        assert col in sch_c, f"Courses thiếu cột {col}"
    sch_p = get_df("PRAGMA table_info(participants)")['name'].tolist()
    for col in ['phone', 'dob']:
        assert col in sch_p, f"Participants thiếu cột {col}"
    print("Tất cả tests passed!")


def main():
    global conn
    conn = init_db()
    if STREAMLIT_AVAILABLE:
        run_app()
    else:
        print("Chạy ở chế độ CLI.")
        run_tests()

if __name__ == '__main__':
    main()
