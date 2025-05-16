import sqlite3
from datetime import datetime
import pandas as pd  # DataFrame operations

# Kiểm tra Streamlit và cấu hình trang
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
    st.set_page_config(page_title="Khoa Giám sát cảnh báo - Quản lý đào tạo", layout="wide")
except ModuleNotFoundError:
    STREAMLIT_AVAILABLE = False

# --------------------
# Database utilities
# --------------------

def init_db(db_path='training.db'):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    # Courses table
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date_created TEXT NOT NULL
        )
    """
    )
    # Add columns if missing
    c.execute("PRAGMA table_info(courses)")
    cols = [row[1] for row in c.fetchall()]
    migrations = [
        ('duration_type', "ALTER TABLE courses ADD COLUMN duration_type TEXT NOT NULL DEFAULT 'Dài hạn'"),
        ('start_date',    "ALTER TABLE courses ADD COLUMN start_date TEXT"),
        ('end_date',      "ALTER TABLE courses ADD COLUMN end_date TEXT"),
        ('image_url',     "ALTER TABLE courses ADD COLUMN image_url TEXT"),
    ]
    for col, ddl in migrations:
        if col not in cols:
            c.execute(ddl)

    # Participants table
    c.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            date_created TEXT NOT NULL
        )
    """
    )
    # Add columns if missing
    c.execute("PRAGMA table_info(participants)")
    cols = [row[1] for row in c.fetchall()]
    migrations = [
        ('phone', "ALTER TABLE participants ADD COLUMN phone TEXT"),
        ('dob',   "ALTER TABLE participants ADD COLUMN dob TEXT"),
    ]
    for col, ddl in migrations:
        if col not in cols:
            c.execute(ddl)

    # Enrollments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            participant_id INTEGER,
            date_enrolled TEXT NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    """
    )
    conn.commit()
    return conn


def get_df(query, params=()):
    """Execute SQL query and return pandas DataFrame."""
    return pd.read_sql_query(query, conn, params=params)

# --------------------
# Streamlit App
# --------------------

def run_app():
    if not STREAMLIT_AVAILABLE:
        print("Streamlit không có sẵn. Vui lòng cài đặt Streamlit để chạy GUI.")
        return

    # Custom CSS for styling
    st.markdown(
        '''
        <style>
            body { background-color: #0E1117; color: #FFFFFF; }
            h1 { color: #FF4B4B; text-align: center; }
            .stButton>button { background-color: #FF4B4B; color: white; border-radius: 8px; }
            .card { background: #1f1f23; border-radius: 10px; padding: 16px; margin-bottom: 16px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        </style>
        ''', unsafe_allow_html=True
    )
    st.title("Khoa Giám sát cảnh báo - Quản lý đào tạo")

    section = st.sidebar.radio(
        "Chọn mục:",
        ["Dashboard", "Thông tin Khóa học", "Quản lý Khóa học", "Thành viên", "Đăng ký"]
    )

    # Dashboard
    if section == "Dashboard":
        st.header("Dashboard")
        dash_type = st.sidebar.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"])
        status_opt = st.sidebar.selectbox("Chọn trạng thái khóa học:", ["Tất cả", "Đang học", "Đã học"])
        # Build status condition
        status_cond = ""
        if status_opt == "Đang học":
            status_cond = "AND c.end_date >= date('now')"
        elif status_opt == "Đã học":
            status_cond = "AND c.end_date < date('now')"
        # Courses by month/year
        df_course_by_month = get_df(
            f"""
            SELECT strftime('%Y-%m', start_date) AS Thời_gian, duration_type AS Loại, COUNT(*) AS Số_lớp
            FROM courses c
            WHERE c.duration_type = ? {status_cond}
            GROUP BY Thời_gian, Loại
            ORDER BY Thời_gian
            """, (dash_type,)
        )
        df_pivot = df_course_by_month.pivot(index='Thời_gian', columns='Loại', values='Số_lớp').fillna(0)
        st.subheader("Số lớp theo tháng/năm")
        st.bar_chart(df_pivot)
        # Registrations per course
        df_reg = get_df(
            f"""
            SELECT c.title AS Khóa_học, COUNT(e.id) AS Số_đăng_ký
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE c.duration_type = ? {status_cond}
            GROUP BY c.title
            ORDER BY Số_đăng_ký DESC
            """, (dash_type,)
        )
        st.subheader("Số người đăng ký theo khóa học")
        st.bar_chart(df_reg.set_index('Khóa_học')['Số_đăng_ký'])

    # Thông tin Khóa học
    elif section == "Thông tin Khóa học":
        st.header("Thông tin Khóa học")
        info_type = st.sidebar.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"])
        df_info = get_df(
            """
            SELECT c.title AS Nội_dung, c.duration_type AS Loại,
                   c.start_date AS 'Ngày bắt đầu', c.end_date AS 'Ngày kết thúc',
                   c.description AS 'Mô tả', c.image_url AS 'Hình ảnh'
            FROM courses c
            WHERE c.duration_type = ?
            ORDER BY c.start_date
            """, (info_type,)
        )
        st.dataframe(df_info[['Nội_dung','Loại','Ngày bắt đầu','Ngày kết thúc','Mô tả']])
        st.subheader(f"Chi tiết thông tin khóa học ({info_type})")
        for _, row in df_info.iterrows():
            st.markdown(f"### {row['Nội_dung']}")
            cols = st.columns([1, 2])
            if row['Hình ảnh']:
                cols[0].image(row['Hình ảnh'], use_container_width=True)
            else:
                cols[0].write("_Chưa có hình ảnh_")
            cols[1].write(row['Mô tả'])

    # Quản lý Khóa học
    elif section == "Quản lý Khóa học":
        st.header("Quản lý Khóa học")
        t1, t2, t3 = st.tabs(["Danh sách", "Thêm mới", "Xóa/Sửa"])
        with t1:
            st.subheader("Danh sách Khóa học")
            df_list = get_df(
                "SELECT title AS 'Nội_dung', duration_type AS 'Loại', start_date AS 'Ngày bắt đầu', end_date AS 'Ngày kết thúc', description AS 'Mô tả', date_created AS 'Ngày tạo' FROM courses"
            )
            st.dataframe(df_list)
        with t2:
            st.subheader("Thêm khóa học mới")
            title = st.text_input("Tên khóa học", key='course_title')
            duration_type = st.selectbox("Loại khóa học:", ["Ngắn hạn","Dài hạn","Seminar"], key='course_duration')
            start = st.date_input("Ngày bắt đầu", key='course_start')
            end = st.date_input("Ngày kết thúc", key='course_end')
            desc = st.text_area("Mô tả khóa học", key='course_desc')
            image_link = st.text_input("URL hình ảnh (nếu có)", key='course_img_link')
            image_file = st.file_uploader("Hoặc upload hình ảnh", type=['png','jpg','jpeg'], key='course_img_file')
            if st.button("Thêm Khóa học"):
                if not title.strip():
                    st.error("Tên khóa học không được để trống.")
                elif start > end:
                    st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    if image_file:
                        import os, uuid
                        os.makedirs('course_images', exist_ok=True)
                        filename = f"{uuid.uuid4()}.{image_file.name.split('.')[-1]}"
                        path = os.path.join('course_images', filename)
                        with open(path,'wb') as f:
                            f.write(image_file.getbuffer())
                        image_url = path
                    else:
                        image_url = image_link or ''
                    conn.execute(
                        "INSERT INTO courses(title,description,date_created,duration_type,start_date,end_date,image_url) VALUES(?,?,?,?,?,?,?)",
                        (title, desc, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration_type, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), image_url)
                    )
                    conn.commit()
                    st.success("Thêm khóa học thành công!")
        with t3:
            st.subheader("Xóa / Sửa Khóa học")
            courses_list = get_df("SELECT id, title, description, duration_type, start_date, end_date FROM courses")
            selected_id = st.selectbox(
                "Chọn Khóa học:", options=courses_list['id'], format_func=lambda x: courses_list[courses_list.id == x]['title'].values[0]
            )
            if st.button("Xóa Khóa học", key='del_course'):
                conn.execute("DELETE FROM courses WHERE id = ?", (selected_id,))
                conn.commit()
                st.success("Xóa khóa học thành công!")
            st.markdown("---")
            course = courses_list[courses_list.id == selected_id].iloc[0]
            edit_title = st.text_input("Tên khóa mới", value=course['title'], key='edit_title')
            edit_duration = st.selectbox(
                "Loại mới:", ["Ngắn hạn","Dài hạn","Seminar"], index=["Ngắn hạn","Dài hạn","Seminar"].index(course['duration_type']), key='edit_duration'
            )
            # Default start date handling
            if course['start_date']:
                try:
                    default_start = datetime.strptime(course['start_date'], "%Y-%m-%d")
                except Exception:
                    default_start = datetime.today()
            else:
                default_start = datetime.today()
            edit_start = st.date_input("Ngày bắt đầu mới", default_start, key='edit_start')
            # Default end date handling
            if course['end_date']:
                try:
                    default_end = datetime.strptime(course['end_date'], "%Y-%m-%d")
                except Exception:
                    default_end = datetime.today()
            else:
                default_end = datetime.today()
            edit_end = st.date_input("Ngày kết thúc mới", default_end, key='edit_end')
            edit_desc = st.text_area("Mô tả mới", value=course['description'], key='edit_desc')
            if st.button("Cập nhật Khóa Học", key='upd_course'):
                if edit_start > edit_end:
                    st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    conn.execute(
                        "UPDATE courses SET title=?, description=?, duration_type=?, start_date=?, end_date=? WHERE id=?",
                        (edit_title, edit_desc, edit_duration, edit_start.strftime("%Y-%m-%d"), edit_end.strftime("%Y-%m-%d"), selected_id)
                    )
                    conn.commit()
                    st.success("Cập nhật khóa học thành công!")

    # Quản lý Thành viên
    elif section == "Thành viên":
        st.header("Quản lý Thành viên")
        t1, t2 = st.tabs(["Danh sách","Thêm mới"])
        with t1:
            df = get_df("SELECT id AS 'Mã', name AS 'Thành viên', email AS 'Email', phone AS 'Số điện thoại', dob AS 'Ngày sinh' FROM participants")
            st.dataframe(df.drop(columns=['Mã']))
        with t2:
            st.subheader("Thêm thành viên mới")
            name = st.text_input("Tên thành viên", key='p_name')
            email = st.text_input("Email thành viên", key='p_email')
            phone = st.text_input("Số điện thoại", key='p_phone')
            dob_input = st.text_input("Ngày sinh (dd/mm/yyyy)", key='p_dob')
            if st.button("Thêm Thành viên"):
                if not name.strip() or not email.strip():
                    st.error("Tên và Email không được để trống.")
                else:
                    try:
                        dob = datetime.strptime(dob_input, "%d/%m/%Y").strftime("%d/%m/%Y")
                    except Exception:
                        st.error("Ngày sinh không hợp lệ. Vui lòng nhập dd/mm/yyyy.")
                    else:
                        try:
                            conn.execute(
                                "INSERT INTO participants(name, email, date_created, phone, dob) VALUES(?,?,?,?,?)", (name, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), phone, dob)
                            )
                            conn.commit()
                            st.success("Thêm thành viên thành công!")
                        except sqlite3.IntegrityError:
                            st.error("Email đã tồn tại.")

# --------------------
# Tests
# --------------------
def run_tests():
    test_conn = init_db(":memory:")
    global conn
    conn = test_conn
    # Table existence tests
    for tbl in ['courses', 'participants', 'enrollments']:
        df = get_df(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        assert not df.empty, f"Bảng {tbl} chưa tồn tại"
    # Courses columns tests
    sch_c = get_df("PRAGMA table_info(courses)")['name'].tolist()
    for col in ['duration_type', 'start_date', 'end_date', 'image_url']:
        assert col in sch_c, f"Courses thiếu cột {col}"
    # Participants columns tests
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
