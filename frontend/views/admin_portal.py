import streamlit as st
from components.api import get_json, patch_json, post_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "User Administration",
        "User lifecycle, account status, password reset support, and role assignment governance.",
    )
    roles = get_json("/api/admin/roles") or []
    users = get_json("/api/admin/users") or []

    role_options = {role["role_name"]: role["role_id"] for role in roles}
    st.subheader("User Management")
    dataframe(
        users,
        columns=[
            "user_id",
            "username",
            "full_name",
            "email",
            "role",
            "department",
            "is_active",
            "last_login",
        ],
        height=300,
    )

    left, right = st.columns(2)
    with left:
        st.write("Create User")
        with st.form("create_user"):
            username = st.text_input("Username")
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            role_name = st.selectbox("Role", list(role_options.keys()) if role_options else [""])
            department = st.text_input("Department", "Clinical Operations")
            password = st.text_input("Temporary password", value="ClinicalDemo!2026", type="password")
            submitted = st.form_submit_button("Create")
        if submitted and role_options:
            result = post_json(
                "/api/admin/users",
                {
                    "username": username,
                    "full_name": full_name,
                    "email": email,
                    "password": password,
                    "role_id": role_options[role_name],
                    "department": department,
                },
            )
            if result:
                st.success("User created.")
                st.rerun()

    with right:
        st.write("Disable or Reassign User")
        if users and role_options:
            selected = st.selectbox("User", [f"{user['user_id']} | {user['username']}" for user in users])
            user_id = int(selected.split(" | ")[0])
            new_role = st.selectbox("New role", list(role_options.keys()), key="new_role")
            active = st.checkbox("Active", value=True)
            if st.button("Apply User Update"):
                result = patch_json(
                    f"/api/admin/users/{user_id}",
                    {"role_id": role_options[new_role], "is_active": active},
                )
                if result:
                    st.success("User updated.")
                    st.rerun()
