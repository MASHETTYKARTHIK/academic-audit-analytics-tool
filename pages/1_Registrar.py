import pandas as pd
import streamlit as st

from db import add_audit_log, add_option, get_all_records, get_options, get_recent_activity, insert_record, update_record, delete_record

st.set_page_config(page_title="Registrar Dashboard", layout="wide", initial_sidebar_state="expanded")

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first")
    st.stop()

if st.session_state.user["role"] != "registrar":
    st.error("Only registrars can access this page")
    st.stop()

st.title("Registrar Dashboard")

st.markdown(
    """
    <style>
    .stApp { background: #f7f9fc; }
    .st-bd, .st-cf { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Manual Entry")
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            student_name = st.text_input("Student Name")
            marks_obtained = st.number_input("Marks Obtained", min_value=0.0, step=1.0)
            max_marks = st.number_input("Max Marks", min_value=0.0, step=1.0, value=100.0)
        with col2:
            section = st.selectbox("Section", options=["All"] + get_options("sections") + ["+ Add new..."], index=0)
            branch = st.selectbox("Branch", options=["All"] + get_options("branches") + ["+ Add new..."], index=0)
            year = st.selectbox("Year", options=["All"] + get_options("years") + ["+ Add new..."], index=0)
            subject = st.selectbox("Subject", options=["All"] + get_options("subjects") + ["+ Add new..."], index=0)

        new_section_value = st.text_input("New Section") if section == "+ Add new..." else ""
        new_branch_value = st.text_input("New Branch") if branch == "+ Add new..." else ""
        new_year_value = st.text_input("New Year") if year == "+ Add new..." else ""
        new_subject_value = st.text_input("New Subject") if subject == "+ Add new..." else ""

        submitted = st.form_submit_button("Save Record")

    if submitted:
        if not student_name.strip() or not marks_obtained or not max_marks:
            st.error("Please fill all fields")
        else:
            selected_section = new_section_value if section == "+ Add new..." and new_section_value else section if section != "All" else ""
            selected_branch = new_branch_value if branch == "+ Add new..." and new_branch_value else branch if branch != "All" else ""
            selected_year = new_year_value if year == "+ Add new..." and new_year_value else year if year != "All" else ""
            selected_subject = new_subject_value if subject == "+ Add new..." and new_subject_value else subject if subject != "All" else ""
            if selected_section:
                add_option("sections", selected_section)
            if selected_branch:
                add_option("branches", selected_branch)
            if selected_year:
                add_option("years", selected_year)
            if selected_subject:
                add_option("subjects", selected_subject)
            insert_record(student_name.strip(), selected_section, selected_branch, selected_year, selected_subject, float(marks_obtained), float(max_marks), st.session_state.user["username"])
            add_audit_log(st.session_state.user["id"], "manual_entry", {"student_name": student_name.strip(), "subject": selected_subject})
            st.success("Record saved")

with st.container(border=True):
    st.subheader("Upload File")
    uploaded_file = st.file_uploader("Upload .xlsx or .csv", type=["xlsx", "csv"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        normalized = {col.strip().lower().replace(" ", "_"): col for col in df.columns}
        expected = ["student_name", "section", "branch", "year", "subject", "marks_obtained", "max_marks"]
        missing = [c for c in expected if c not in normalized]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
        else:
            preview_rows = []
            for _, row in df.iterrows():
                preview_rows.append(
                    {
                        "student_name": str(row[normalized["student_name"]]).strip(),
                        "section": str(row[normalized["section"]]).strip(),
                        "branch": str(row[normalized["branch"]]).strip(),
                        "year": str(row[normalized["year"]]).strip(),
                        "subject": str(row[normalized["subject"]]).strip(),
                        "marks_obtained": float(row[normalized["marks_obtained"]]),
                        "max_marks": float(row[normalized["max_marks"]]),
                    }
                )
            st.dataframe(pd.DataFrame(preview_rows))
            if st.button("Confirm Upload"):
                for record in preview_rows:
                    for field in ["section", "branch", "year", "subject"]:
                        if record[field]:
                            add_option({"section": "sections", "branch": "branches", "year": "years", "subject": "subjects"}[field], record[field])
                    insert_record(record["student_name"], record["section"], record["branch"], record["year"], record["subject"], float(record["marks_obtained"]), float(record["max_marks"]), st.session_state.user["username"])
                add_audit_log(st.session_state.user["id"], "upload", {"rows": len(preview_rows)})
                st.success("Upload completed")

with st.container(border=True):
    st.subheader("View / Edit Data")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        section_filter = st.selectbox("Section Filter", options=["All"] + get_options("sections"), key="section_filter")
    with filter_col2:
        branch_filter = st.selectbox("Branch Filter", options=["All"] + get_options("branches"), key="branch_filter")
    with filter_col3:
        year_filter = st.selectbox("Year Filter", options=["All"] + get_options("years"), key="year_filter")
    with filter_col4:
        subject_filter = st.selectbox("Subject Filter", options=["All"] + get_options("subjects"), key="subject_filter")

    filters = {k: v for k, v in {"section": section_filter, "branch": branch_filter, "year": year_filter, "subject": subject_filter}.items() if v != "All"}
    records = get_all_records(filters)
    if records:
        edited_df = pd.DataFrame(records)
        edited_df["delete"] = False
        edited_df = edited_df[["id", "delete", "student_name", "section", "branch", "year", "subject", "marks_obtained", "max_marks", "entered_by", "created_at", "updated_at"]]
        edited = st.data_editor(
            edited_df,
            use_container_width=True,
            hide_index=True,
            disabled=["id", "entered_by", "created_at", "updated_at"],
            column_config={"delete": st.column_config.CheckboxColumn("Delete", help="Mark rows to delete")},
        )
        if st.button("Save Changes"):
            for _, row in edited.iterrows():
                if pd.notna(row["id"]):
                    if bool(row["delete"]):
                        delete_record(int(row["id"]))
                    else:
                        update_record(int(row["id"]), row["student_name"], row["section"], row["branch"], row["year"], row["subject"], float(row["marks_obtained"]), float(row["max_marks"]))
            st.success("Changes saved")
    else:
        st.info("No records found")

st.subheader("Recent Activity")
activity = get_recent_activity(10)
if activity:
    st.dataframe(pd.DataFrame(activity))
else:
    st.info("No activity yet")
