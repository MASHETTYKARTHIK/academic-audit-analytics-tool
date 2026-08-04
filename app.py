"""Application entry point for the Administrator Academic Audit dashboard."""

from __future__ import annotations

import streamlit as st

from config.config import get_application_config
from database.database import execute_query, initialize_database
from database.seed import seed_database
from modules.dashboard import render_administrator_dashboard
from utils.logger import configure_logging, get_logger

LOGGER = get_logger(__name__)


@st.cache_resource(show_spinner=False)
def _initialize_application() -> bool:
    """Initialize the schema and seed only a newly empty database.

    Cached resource initialization prevents Streamlit reruns from repeatedly
    executing schema setup or evaluating the seed state in one server process.
    """
    initialize_database()
    row = execute_query("SELECT COUNT(*) AS record_count FROM departments")
    is_empty = not row or int(row[0]["record_count"]) == 0
    if is_empty:
        summary = seed_database()
        LOGGER.info("Initialized empty academic audit database: %s", summary)
    else:
        LOGGER.debug("Using existing academic audit database without reseeding.")
    return is_empty


def _render_navigation() -> None:
    """Render the administrator-only navigation and future disabled areas."""
    st.sidebar.markdown(
        "<h2 style='margin-bottom:0;'>🎓 Academic Audit Analytics Tool</h2>"
        "<p style='color:#94a3b8; margin-top:.2rem;'>Administrator Portal</p>",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()
    st.sidebar.radio(
        "Current workspace",
        options=["🏠 Administrator Dashboard"],
        label_visibility="collapsed",
    )
    st.sidebar.markdown("<small>Navigation</small>", unsafe_allow_html=True)
    st.sidebar.button("📄 Reports · Coming Soon", disabled=True, width="stretch")
    st.sidebar.button("⚙️ Settings · Coming Soon", disabled=True, width="stretch")
    st.sidebar.button("❓ Help · Coming Soon", disabled=True, width="stretch")


def main() -> None:
    """Configure Streamlit, prepare the database, and render the dashboard."""
    application_config = get_application_config()
    st.set_page_config(
        page_title=application_config.page_title,
        page_icon=application_config.page_icon,
        layout=application_config.layout,
        initial_sidebar_state=application_config.initial_sidebar_state,
    )
    configure_logging()

    try:
        _initialize_application()
    except FileNotFoundError:
        LOGGER.exception("The database schema file is unavailable.")
        st.error("Application setup failed because the database schema is missing.")
        st.stop()
    except (OSError, RuntimeError) as error:
        LOGGER.exception("Unable to initialize the academic audit database.")
        st.error("The academic audit database could not be initialized.")
        with st.expander("Technical details"):
            st.code(str(error))
        st.stop()
    except Exception as error:  # pragma: no cover - final UI safety boundary
        LOGGER.exception("Unexpected application initialization failure.")
        st.error("An unexpected error occurred while preparing the application.")
        with st.expander("Technical details"):
            st.code(str(error))
        st.stop()

    _render_navigation()
    try:
        render_administrator_dashboard()
    except Exception as error:  # pragma: no cover - final UI safety boundary
        LOGGER.exception("Administrator dashboard rendering failed.")
        st.error("The dashboard could not be rendered. Please refresh and try again.")
        with st.expander("Technical details"):
            st.code(str(error))


if __name__ == "__main__":
    main()
