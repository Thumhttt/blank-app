import sqlite3
from datetime import datetime
import os
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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date_created TEXT NOT NULL,
            duration_type TEXT NOT NULL DEFAULT 'Dài hạn',
            start_date TEXT,
            end_date TEXT,
            image_url TEXT,
            ref_url TEXT
        )
        """
    )
    # Add missing columns to courses
    c.execute("PRAGMA table_info(courses)")
    existing = [col[1] for col in c.fetchall()]
    for column, ddl in [
        ('duration_type', "ALTER TABLE courses ADD COLUMN duration_type TEXT NOT NULL DEFAULT 'Dài hạn'"),
        ('start_date',    "ALTER TABLE courses ADD COLUMN start_date TEXT"),
        ('end_date',      "ALTER TABLE courses ADD COLUMN end_date TEXT"),
        ('image_url',     "ALTER TABLE courses ADD COLUMN image_url TEXT"),
        ('ref_url',       "ALTER TABLE courses ADD COLUMN ref_url TEXT"),
    ]:
        if column not in existing:
            c.execute(ddl)
    # Participants table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            date_created TEXT NOT NULL
        )
        """
    )
    c.execute("PRAGMA table_info(participants)")
    existing = [col[1] for col in c.fetchall()]
    if 'phone' not in existing:
        c.execute("ALTER TABLE participants ADD COLUMN phone TEXT")
    # Enrollments table
    c.execute(
        """
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
    return pd.read_sql_query(query, conn, params=params)

# Ensure uploads directory exists
os.makedirs('uploads', exist_ok=True)

# --------------------
# Streamlit App
# --------------------
def run_app():
    if not STREAMLIT_AVAILABLE:
        print("Streamlit không có sẵn. Vui lòng cài đặt để chạy GUI.")
        return

    # Custom CSS
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
            body { font-family: 'Poppins', sans-serif; background-color: #0E1117; color: #FFFFFF; }
            .stButton>button { font-family: 'Poppins', sans-serif; background-color: #FF4B4B; color: white; border-radius: 8px; }
            .sidebar .sidebar-content { background: linear-gradient(180deg, #FF4B4B 0%, #FF9E9E 100%); }
            .card { background: #1f1f23; border-radius: 10px; padding: 24px; margin: 16px 0; box-shadow: 0 8px 16px rgba(0,0,0,0.4); }
        </style>
        """, unsafe_allow_html=True
    )

    # Sidebar navigation
    section = st.sidebar.radio(
        "Chọn mục:",
        ["Dashboard", "Thông tin Khóa học", "Quản lý Khóa học", "Thành viên", "Đăng ký"]
    )
    info_type = reg_type = mgmt_type = None
    if section == "Thông tin Khóa học":
        info_type = st.sidebar.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"], key='info_type')
    elif section == "Đăng ký":
        reg_type = st.sidebar.selectbox("Chọn loại đào tạo để đăng ký:", ["Ngắn hạn", "Dài hạn", "Seminar"], key='reg_type')
    elif section == "Quản lý Khóa học":
        mgmt_type = st.sidebar.selectbox("Chọn loại đào tạo:", ["Ngắn hạn", "Dài hạn", "Seminar"], key='mgmt_type')

    # Dashboard
    if section == "Dashboard":
        st.markdown("<h1 style='text-align:center; font-size:48px;'>Khoa Giám sát cảnh báo - Quản lý đào tạo</h1>", unsafe_allow_html=True)
        st.header("Dashboard")

        total_c = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        total_p = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
        col1, col2 = st.columns(2)
        col1.metric("Khóa học", total_c)
        col2.metric("Thành viên", total_p)

        df_ct = get_df("SELECT duration_type AS Loại, COUNT(*) AS Số_khóa FROM courses GROUP BY duration_type")
        if not df_ct.empty:
            cols = st.columns(len(df_ct))
            for i, row in df_ct.iterrows():
                cols[i].metric(row['Loại'], row['Số_khóa'])
        else:
            st.info("Chưa có khóa nào được phân loại.")

        st.subheader("Các khóa sắp bắt đầu")
        today = datetime.now().strftime('%Y-%m-%d')
        df_up = get_df(
            """
            SELECT id, title, duration_type, start_date, description, image_url, ref_url
            FROM courses
            WHERE start_date >= ?
            ORDER BY start_date ASC
            LIMIT 5
            """, (today,)
        )
        if df_up.empty:
            st.info("Không có khóa học nào sắp bắt đầu.")
        else:
            for _, r in df_up.iterrows():
                st.markdown(f"### {r['title']}")
                c1, c2 = st.columns([1,2])
                if r['image_url']:
                    c1.image(r['image_url'], use_container_width=True)
                else:
                    c1.write("_Không có hình ảnh_")
                c2.markdown(f"**Loại**: {r['duration_type']}")
                c2.markdown(f"**Ngày bắt đầu**: {pd.to_datetime(r['start_date']).strftime('%d/%m/%Y')}")
                c2.write(r['description'] or "_Không có mô tả_")
                if r['ref_url']:
                    c2.markdown(f"[Tài liệu tham khảo]({r['ref_url']})")
                df_en = get_df(
                    "SELECT p.name FROM enrollments e JOIN participants p ON e.participant_id = p.id WHERE e.course_id = ?", (r['id'],)
                )
                c2.markdown("**Đã đăng ký:** " + (", ".join(df_en['name']) if not df_en.empty else "_Chưa có_"))

    # Thông tin Khóa học
    elif section == "Thông tin Khóa học":
        st.header("Thông tin Khóa học")
        df_info = get_df(
            """
            SELECT id AS cid, title AS Nội_dung, duration_type AS Loại,
                   start_date AS ngày_bd, end_date AS ngày_kt,
                   description AS Mô_tả, image_url AS Hình_ảnh, ref_url AS Tài_liệu
            FROM courses
            WHERE duration_type = ?
            ORDER BY ngày_bd
            """, (info_type,)
        )
        df_info['Ngày bắt đầu'] = pd.to_datetime(df_info['ngày_bd'], errors='coerce').dt.strftime('%d/%m/%Y')
        df_info['Ngày kết thúc'] = pd.to_datetime(df_info['ngày_kt'], errors='coerce').dt.strftime('%d/%m/%Y')
        st.dataframe(df_info[['Nội_dung','Loại','Ngày bắt đầu','Ngày kết thúc','Mô_tả']])
        for _, r in df_info.iterrows():
            st.markdown(f"### {r['Nội_dung']}")
            c1, c2 = st.columns([1,2])
            if r['Hình_ảnh']:
                c1.image(r['Hình_ảnh'], use_container_width=True)
            else:
                c1.write("_Không có hình ảnh_")
            c2.write(r['Mô_tả'])
            if r['Tài_liệu']:
                c2.markdown(f"[Tài liệu tham khảo]({r['Tài_liệu']})")
            df_en = get_df(
                "SELECT p.name, p.email FROM enrollments e JOIN participants p ON e.participant_id = p.id WHERE e.course_id = ?", (r['cid'],)
            )
            c2.markdown("**Đã đăng ký:**")
            c2.dataframe(df_en.reset_index(drop=True))

    # Quản lý Khóa học
    elif section == "Quản lý Khóa học":
        st.header("Quản lý Khóa học")
        tabs = st.tabs(["Danh sách","Thêm mới","Xóa/Sửa"])
        with tabs[0]:
            st.subheader("Danh sách khóa")
            df_list = get_df(
                "SELECT id, title AS Nội_dung, duration_type AS Loại, start_date AS ngày_bd, end_date AS ngày_kt, description AS Mô_tả FROM courses WHERE duration_type = ?", (mgmt_type,)
            )
            df_list['Ngày bắt đầu'] = pd.to_datetime(df_list['ngày_bd'], errors='coerce').dt.strftime('%d/%m/%Y')
            df_list['Ngày kết thúc'] = pd.to_datetime(df_list['ngày_kt'], errors='coerce').dt.strftime('%d/%m/%Y')
            st.dataframe(df_list[['Nội_dung','Loại','Ngày bắt đầu','Ngày kết thúc','Mô_tả']])
        with tabs[1]:
            st.subheader("Thêm khóa mới")
            title = st.text_input("Tên khóa")
            dtype = st.selectbox("Loại đào tạo",["Ngắn hạn","Dài hạn","Seminar"])
            sd = st.date_input("Ngày bắt đầu")
            ed = st.date_input("Ngày kết thúc")
            desc = st.text_area("Mô tả")
            up_img = st.file_uploader("Upload hình ảnh", type=["png","jpg","jpeg"])
            img_url = ''
            if up_img:
                path = f"uploads/{up_img.name}"; open(path,'wb').write(up_img.getbuffer()); img_url = path
            else:
                img_url = st.text_input("URL hình ảnh (nếu có)")
            ref_url = st.text_input("Link tài liệu tham khảo")
            if st.button("Thêm khóa"):
                if not title.strip(): st.error("Tên khóa không được để trống.")
                elif sd > ed: st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    conn.execute(
                        "INSERT INTO courses(title,description,date_created,duration_type,start_date,end_date,image_url,ref_url) VALUES(?,?,?,?,?,?,?,?)",
                        (title, desc, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dtype, sd.strftime('%Y-%m-%d'), ed.strftime('%Y-%m-%d'), img_url, ref_url)
                    )
                    conn.commit(); st.success("Thêm khóa thành công!")
        with tabs[2]:
            st.subheader("Xóa/Sửa khóa")
            cl = get_df("SELECT id,title,duration_type,start_date,end_date,description FROM courses WHERE duration_type = ?", (mgmt_type,))
            if cl.empty:
                st.warning("Không có khóa nào.")
            else:
                sel = st.selectbox("Chọn khóa", cl['id'], format_func=lambda x: cl[cl.id==x]['title'].values[0])
                if st.button("Xóa khóa"): conn.execute("DELETE FROM courses WHERE id=?",(sel,));conn.commit(); st.success("Xóa thành công!")
                st.markdown("---")
                rec = cl[cl.id==sel].iloc[0]
                new_title = st.text_input("Tên mới", rec.title)
                new_type = st.selectbox("Loại mới",["Ngắn hạn","Dài hạn","Seminar"], index=["Ngắn hạn","Dài hạn","Seminar"].index(rec.duration_type))
                new_sd = st.date_input("Ngày bắt đầu mới", datetime.strptime(rec.start_date,'%Y-%m-%d'))
                new_ed = st.date_input("Ngày kết thúc mới", datetime.strptime(rec.end_date,'%Y-%m-%d'))
                new_desc = st.text_area("Mô tả mới", rec.description)
                if st.button("Cập nhật khóa"): 
                    conn.execute(
                        "UPDATE courses SET title=?,description=?,duration_type=?,start_date=?,end_date=? WHERE id=?",(new_title,new_desc,new_type,new_sd.strftime('%Y-%m-%d'),new_ed.strftime('%Y-%m-%d'),sel)
                    )
                    conn.commit(); st.success("Cập nhật thành công!")

    # Thành viên
    elif section == "Thành viên":
        st.header("Quản lý Thành viên")
        tabs2 = st.tabs(["Danh sách","Thêm mới","Xóa/Sửa"])
        with tabs2[0]:
            st.subheader("Danh sách Thành viên")
            dfp = get_df("SELECT name AS 'Họ và tên', email AS Email, phone AS 'Số điện thoại' FROM participants")
            st.dataframe(dfp)
        with tabs2[1]:
            st.subheader("Thêm Thành viên")
            nm = st.text_input("Họ và tên")
            em = st.text_input("Email")
            ph = st.text_input("Số điện thoại")
            if st.button("Thêm"): 
                if not nm or not em: st.error("Họ tên và email không được để trống.")
                else:
                    try: conn.execute("INSERT INTO participants(name,email,phone,date_created) VALUES(?,?,?,?)",(nm,em,ph,datetime.now().strftime('%Y-%m-%d %H:%M:%S')));conn.commit();st.success("Thêm thành công!")
                    except sqlite3.IntegrityError: st.error("Email đã tồn tại.")
        with tabs2[2]:
            st.subheader("Xóa/Sửa Thành viên")
            pl = get_df("SELECT id,name,email,phone FROM participants")
            if pl.empty: st.warning("Chưa có thành viên.")
            else:
                sid = st.selectbox("Chọn thành viên", pl['id'], format_func=lambda x: pl[pl.id==x]['name'].values[0])
                if st.button("Xóa"): conn.execute("DELETE FROM participants WHERE id=?",(sid,));conn.commit();st.success("Xóa thành công!")
                st.markdown("---")
                mem = pl[pl.id==sid].iloc[0]
                nm2 = st.text_input("Họ và tên mới", mem.name)
                em2 = st.text_input("Email mới", mem.email)
                ph2 = st.text_input("Số điện thoại mới", mem.phone)
                if st.button("Cập nhật"): 
                    try: conn.execute("UPDATE participants SET name=?,email=?,phone=? WHERE id=?",(nm2,em2,ph2,sid));conn.commit();st.success("Cập nhật thành công!")
                    except sqlite3.IntegrityError: st.error("Email đã tồn tại.")

    # Đăng ký
    elif section == "Đăng ký":
        st.header("Đăng ký Khóa học")
        df_courses = get_df("SELECT id,title FROM courses WHERE duration_type=?",(reg_type,))
        df_members = get_df("SELECT id,name FROM participants")
        if df_courses.empty or df_members.empty:
            st.warning("Thiếu dữ liệu.")
        else:
            cid = st.selectbox("Chọn khóa", df_courses['id'], format_func=lambda x: df_courses[df_courses.id==x]['title'].values[0])
            mid = st.selectbox("Chọn thành viên", df_members['id'], format_func=lambda x: df_members[df_members.id==x]['name'].values[0])
            if st.button("Ghi danh"): 
                conn.execute("INSERT INTO enrollments(course_id,participant_id,date_enrolled) VALUES(?,?,?)",(cid,mid,datetime.now().strftime('%d/%m/%Y')))
                conn.commit()
                st.success("Ghi danh thành công!")
        df_reg = get_df(
            """
            SELECT
              e.id AS rid,
              p.name AS "Thành viên",
              c.title AS "Khóa",
              e.date_enrolled AS "Ngày đk"
            FROM enrollments e
            JOIN participants p ON e.participant_id = p.id
            JOIN courses c ON e.course_id = c.id
            WHERE c.duration_type = ?
            """, (reg_type,)
        )
        if df_reg.empty:
            st.info("Chưa có đăng ký.")
        else:
            sel = st.selectbox(
                "Chọn đăng ký để xóa", df_reg['rid'],
                format_func=lambda x: f"{df_reg[df_reg.rid==x]['Thành viên'].values[0]} - {df_reg[df_reg.rid==x]['Khóa'].values[0]}"
            )
            if st.button("Xóa đăng ký"):
                conn.execute("DELETE FROM enrollments WHERE id=?",(sel,))
                conn.commit()
                st.success("Xóa thành công!")
            df_reg['Ngày đk'] = pd.to_datetime(df_reg['Ngày đk'], dayfirst=True).dt.strftime('%d/%m/%Y')
            st.dataframe(df_reg[['Thành viên','Khóa','Ngày đk']])

# --------------------
if __name__ == '__main__':
    conn = init_db()
    if STREAMLIT_AVAILABLE:
        run_app()
    else:
        print("Streamlit không khả dụng...")
