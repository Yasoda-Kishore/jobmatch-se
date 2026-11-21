"""JobMatch SE web app. Start the API first, then run:  streamlit run ui/app.py"""
import os
from collections import Counter

import httpx
import streamlit as st

API_URL = os.getenv("JOBMATCH_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="JobMatch SE", page_icon="🔎", layout="wide")
st.title("JobMatch SE")
st.caption("Find Swedish IT jobs that fit your CV. Live ads from Arbetsförmedlingen (JobTech API).")

page = st.sidebar.radio("Page", ["Match my CV", "Search jobs"])
city = st.sidebar.text_input("City (optional)", placeholder="e.g. Stockholm") or None
language_label = st.sidebar.selectbox("Ad language", ["Any", "English", "Swedish"])
language = {"Any": None, "English": "en", "Swedish": "sv"}[language_label]


def api_is_up() -> bool:
    try:
        return httpx.get(f"{API_URL}/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


if not api_is_up():
    st.error(f"The API is not running at {API_URL}. Start it with: uvicorn jobmatch.api.main:app")
    st.stop()


def show_match(m: dict) -> None:
    """One job as a card: score, skills, reasons and a link to the ad."""
    with st.container(border=True):
        left, right = st.columns([4, 1])
        left.subheader(m["title"])
        left.write(f"{m['employer'] or 'Unknown employer'} · {m['city'] or 'No city given'}")
        right.metric("Fit", f"{m['score']}/100")
        st.progress(m["score"] / 100)
        if m["requires_swedish"]:
            st.warning("Swedish is required for this job")
        st.write("**You have:** " + (", ".join(m["matching_skills"]) or "-"))
        st.write("**Missing:** " + (", ".join(m["missing_skills"]) or "-"))
        for reason in m["reasons"]:
            st.write(f"- {reason}")
        with st.expander("How this score was calculated"):
            st.json(m["score_parts"])
        if m.get("url"):
            st.link_button("Open the ad", m["url"])


if page == "Match my CV":
    st.header("Match my CV")
    st.write("Upload your CV as a PDF. It is read by a local AI model and is not stored.")
    cv = st.file_uploader("Your CV", type=["pdf"])
    top = st.slider("How many jobs to score", 1, 10, 5)
    if cv and st.button("Find my matches", type="primary"):
        with st.spinner("Reading your CV and scoring jobs. This takes a few minutes on a laptop..."):
            response = httpx.post(
                f"{API_URL}/match",
                params={k: v for k, v in {"city": city, "language": language, "top": top}.items() if v},
                files={"cv": (cv.name, cv.getvalue(), "application/pdf")},
                timeout=900,
            )
        if response.status_code != 200:
            st.error(f"Something went wrong: {response.text}")
            st.stop()
        result = response.json()
        profile = result["profile"]

        st.subheader("Your profile")
        col1, col2, col3 = st.columns(3)
        col1.metric("Experience", f"{profile['years_of_experience']} years")
        col2.metric("Skills found", len(profile["skills"]))
        col3.metric("Jobs scored", len(result["matches"]))
        st.write("**Roles:** " + ", ".join(profile["target_roles"]))
        st.write("**Skills:** " + ", ".join(profile["skills"]))

        st.subheader("Your best matches")
        for match in result["matches"]:
            show_match(match)

        gaps = Counter(s for m in result["matches"] for s in m["missing_skills"])
        if gaps:
            st.subheader("Skills to learn next")
            st.write("Skills that your best matches ask for, and how many of them ask:")
            st.bar_chart({skill: count for skill, count in gaps.most_common(8)}, horizontal=True)

else:
    st.header("Search jobs")
    question = st.text_input("What are you looking for?", placeholder="e.g. machine learning engineer")
    mode = st.selectbox("Search method", ["hybrid", "vector", "keyword", "rerank"])
    if question and len(question) >= 2:
        response = httpx.get(
            f"{API_URL}/search",
            params={k: v for k, v in {"q": question, "mode": mode, "city": city, "language": language}.items() if v},
            timeout=120,
        )
        if response.status_code != 200:
            st.error(f"Something went wrong: {response.text}")
            st.stop()
        results = response.json()["results"]
        st.write(f"{len(results)} results")
        st.dataframe(
            [{"Title": r["title"], "Employer": r["employer"], "City": r["city"],
              "Language": r["language"], "Ad": r["url"]} for r in results],
            column_config={"Ad": st.column_config.LinkColumn("Ad", display_text="Open")},
            hide_index=True,
            width="stretch",
        )