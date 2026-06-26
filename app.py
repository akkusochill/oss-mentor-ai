"""
OSS Mentor AI — Streamlit Application
======================================
Analyzes GitHub repositories and helps developers find the right open-source
contribution opportunities using the GitHub API and Gemini AI.

Features:
  - Repository metadata analysis (stars, forks, issues, contributors)
  - Health Score, Activity Score, Repository Rating
  - Topic-based smart skill matching with explanations
  - AI-generated repository summary (Gemini)
  - AI Roadmap & Contribution Recommendation (Gemini)
  - Contributor Activity Chart (bar chart via pandas)
  - Issue filtering (All / Beginner / Documentation)
  - README preview
  - Language breakdown
  - Suggested repositories sidebar
"""

import os
from datetime import datetime

import google.generativeai as genai
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# ── Environment & Gemini setup ─────────────────────────────────────────────────
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ── Constants ──────────────────────────────────────────────────────────────────

# Keywords that indicate a beginner-friendly issue
BEGINNER_KEYWORDS = [
    "good first issue",
    "beginner",
    "easy",
    "documentation",
    "help wanted",
]

# Skill → suggested repo mapping for the sidebar
RECOMMENDED_REPOS: dict[str, list[str]] = {
    "Python": [
        "https://github.com/pallets/flask",
        "https://github.com/streamlit/streamlit",
    ],
    "JavaScript": [
        "https://github.com/facebook/react",
        "https://github.com/vercel/next.js",
    ],
    "TypeScript": [
        "https://github.com/microsoft/TypeScript",
    ],
    "C++": [
        "https://github.com/opencv/opencv",
    ],
    "AI/ML": [
        "https://github.com/scikit-learn/scikit-learn",
        "https://github.com/huggingface/transformers",
    ],
}

# Topic → skill mappings used for enhanced skill matching.
# Keys are GitHub topic strings; values are lists of user-skill labels.
TOPIC_SKILL_MAP: dict[str, list[str]] = {
    "python":        ["Python"],
    "flask":         ["Python"],
    "django":        ["Python"],
    "fastapi":       ["Python"],
    "javascript":    ["JavaScript"],
    "typescript":    ["TypeScript"],
    "react":         ["React", "JavaScript"],
    "nextjs":        ["JavaScript", "TypeScript"],
    "nodejs":        ["Node.js", "JavaScript"],
    "html":          ["HTML"],
    "css":           ["CSS"],
    "sql":           ["SQL"],
    "machine-learning": ["AI/ML"],
    "deep-learning": ["AI/ML"],
    "data-science":  ["AI/ML", "Data Analysis"],
    "nlp":           ["AI/ML"],
    "java":          ["Java"],
    "cpp":           ["C++"],
    "c-plus-plus":   ["C++"],
    "swift":         ["Swift", "SwiftUI"],
    "swiftui":       ["SwiftUI"],
    "ios":           ["Swift", "SwiftUI"],
}

# All supported skill labels (used in the multiselect)
ALL_SKILLS = [
    "Python", "C", "C++", "Java", "JavaScript", "TypeScript",
    "HTML", "CSS", "React", "Node.js", "Swift", "SwiftUI",
    "Git", "GitHub", "SQL", "AI/ML", "Data Analysis",
]

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OSS Mentor AI",
    page_icon="🚀",
    layout="wide",
)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def parse_repo_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.
    Raises ValueError on invalid input.
    """
    parts = url.strip().strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL.")
    return parts[-2], parts[-1]


def github_get(url: str, headers: dict | None = None) -> requests.Response:
    """Thin wrapper around requests.get with optional headers."""
    return requests.get(url, headers=headers or {})


def compute_activity_score(stars: int, forks: int, contributors: int, open_issues: int) -> int:
    """
    Return an activity score 0–100 based on repo vitality signals.
    Each quadrant contributes 25 points.
    """
    score = 0
    if stars > 100:
        score += 25
    if contributors > 10:
        score += 25
    if forks > 50:
        score += 25
    if open_issues < 100:
        score += 25
    return score


def compute_health_score(stars: int, open_issues: int, has_description: bool, has_language: bool) -> int:
    """
    Return a health score 0–100 reflecting repository quality signals.
    """
    score = 0
    if stars > 100:
        score += 30
    if open_issues < 100:
        score += 30
    if has_description:
        score += 20
    if has_language:
        score += 20
    return score


def compute_difficulty(stars: int, open_issues: int) -> str:
    """Return a beginner-friendliness label."""
    if stars > 500 and open_issues < 50:
        return "🟢 Beginner Friendly"
    elif stars > 100:
        return "🟡 Intermediate"
    return "🔴 Advanced"


def compute_repo_rating(overall_score: float) -> tuple[str, str]:
    """
    Return (label, sentiment) for the overall score.
    sentiment is one of: 'success', 'info', 'warning'.
    """
    if overall_score >= 80:
        return "🌟 Excellent", "success"
    elif overall_score >= 60:
        return "⭐ Good", "info"
    elif overall_score >= 40:
        return "🟡 Average", "warning"
    return "🔴 Poor", "warning"


def compute_skill_match(
    repo_language: str | None,
    topics: list[str],
    user_skills: list[str],
) -> tuple[int, list[str]]:
    """
    Enhanced skill matching that considers both the primary repo language
    and its GitHub topics.

    Returns:
        match_score  : int  0–100
        reasons      : list of human-readable bullet strings
    """
    score = 0
    reasons: list[str] = []

    # 1. Primary language match (worth 50 points)
    if repo_language and repo_language in user_skills:
        score += 50
        reasons.append(f"✅ **Language match** — repository uses **{repo_language}**, which is in your skill set.")

    # 2. Topic-based matches (up to 30 points, +10 per unique skill hit)
    matched_via_topic: set[str] = set()
    for topic in topics:
        topic_lower = topic.lower()
        mapped_skills = TOPIC_SKILL_MAP.get(topic_lower, [])
        for mapped in mapped_skills:
            if mapped in user_skills and mapped not in matched_via_topic:
                matched_via_topic.add(mapped)
                score += 10
                reasons.append(f"✅ **Topic match** — topic `{topic}` aligns with your **{mapped}** skill.")

    # Cap topic contribution at 30 points
    topic_contribution = min(len(matched_via_topic) * 10, 30)
    # (Already added above; trim excess if over 30)
    if len(matched_via_topic) * 10 > 30:
        over = len(matched_via_topic) * 10 - 30
        score -= over

    # 3. Git / GitHub bonus (up to 20 points)
    if "Git" in user_skills:
        score += 10
        reasons.append("✅ **Git knowledge** — you know Git, which is required for any contribution.")
    if "GitHub" in user_skills:
        score += 10
        reasons.append("✅ **GitHub familiarity** — you're comfortable with GitHub workflows.")

    # 4. If no direct match found, explain
    if score == 0:
        reasons.append("ℹ️ No direct skill overlap detected between your skills and this repository's language/topics.")

    score = min(score, 100)
    return score, reasons


def readiness_label(readiness_score: int) -> tuple[str, str]:
    """
    Return (message, streamlit_level) for the readiness score.
    streamlit_level: 'success' | 'warning' | 'error'
    """
    if readiness_score >= 80:
        return "🟢 Excellent Match — You're ready to contribute!", "success"
    elif readiness_score >= 60:
        return "🟡 Moderate Match — A bit of preparation will help.", "warning"
    elif readiness_score >= 40:
        return "🔴 Low Skill Match — Consider learning the primary tech stack first.", "error"
    return "🔴 Low Skill Match — This repo may be outside your current skill set.", "error"


@st.cache_data(show_spinner=False)
def generate_ai_summary(
    repo_name: str,
    description: str,
    language: str,
    stars: int,
    forks: int,
    topics: list[str],
    recent_issue_titles: list[str],
    user_skills: list[str],
) -> str:
    """
    Call Gemini to produce a structured repository overview.
    Cached by Streamlit so repeated renders won't re-call the API.
    """
    topics_str = ", ".join(topics) if topics else "None"
    issues_str = "\n".join(f"- {t}" for t in recent_issue_titles[:10]) if recent_issue_titles else "None"
    skills_str = ", ".join(user_skills) if user_skills else "None selected"

    prompt = f"""
You are an expert open-source mentor. Given the repository information below,
write a concise, friendly overview for a developer exploring this project.

Repository Name: {repo_name}
Description: {description or "N/A"}
Primary Language: {language or "Mixed/Unknown"}
Stars: {stars}
Forks: {forks}
Topics: {topics_str}
Recent Issue Titles:
{issues_str}
User's Skills: {skills_str}

Please address EXACTLY these five points (use the numbered headings):
1. **What this repository does** — one short paragraph
2. **Beginner friendliness** — is it a good first-contribution project? Why?
3. **Main technologies** — list the primary tech stack
4. **Why it matches this user's skills** — specific to the skills listed above
5. **Suggested first contribution** — one concrete, actionable suggestion

Keep the entire response under 400 words. Be specific and encouraging.
"""
    response = model.generate_content(prompt)
    return response.text


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("🚀 OSS Mentor AI")
    st.write(
        "Analyze GitHub repositories and discover beginner-friendly "
        "open source contribution opportunities."
    )
    st.divider()

    st.write("### Features")
    st.write("✅ Repository Analysis")
    st.write("✅ Smart Skill Matching")
    st.write("✅ Contribution Difficulty")
    st.write("✅ AI Roadmaps")
    st.write("✅ Contribution Recommendations")
    st.write("✅ Activity Chart")

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE — INPUTS
# ══════════════════════════════════════════════════════════════════════════════

st.title("🚀 OSS Mentor AI")
st.caption("Discover the perfect open-source project and make your first contribution with AI guidance.")
st.divider()

repo_url = st.text_input(
    "🔗 Enter a GitHub Repository URL",
    placeholder="https://github.com/owner/repo",
)

skills = st.multiselect(
    "🛠️ Select Your Skills",
    ALL_SKILLS,
    help="Select all technologies you're comfortable with.",
)

# Populate sidebar with suggested repos once skills are known
with st.sidebar:
    if skills:
        st.divider()
        st.write("### 🎯 Suggested Repositories")
        shown: set[str] = set()
        for skill in skills:
            for repo_link in RECOMMENDED_REPOS.get(skill, []):
                if repo_link not in shown:
                    st.link_button(repo_link.split("/")[-1], repo_link)
                    shown.add(repo_link)

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS — triggered by button click
# ══════════════════════════════════════════════════════════════════════════════

if st.button("🔍 Analyze Repository", type="primary"):

    if not repo_url:
        st.warning("Please enter a GitHub repository URL.")
        st.stop()

    try:
        # ── 1. Parse URL ───────────────────────────────────────────────────────
        owner, repo = parse_repo_url(repo_url)

        # ── 2. Fetch repository metadata ───────────────────────────────────────
        with st.spinner("Fetching repository data…"):
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_response = github_get(api_url)

            if repo_response.status_code != 200:
                st.error("❌ Repository not found. Please verify the URL and try again.")
                st.stop()

            data = repo_response.json()

            # README (raw text, first 3000 chars)
            readme_response = github_get(
                f"https://api.github.com/repos/{owner}/{repo}/readme",
                headers={"Accept": "application/vnd.github.raw"},
            )
            readme_text = readme_response.text[:3000] if readme_response.status_code == 200 else ""

            # Language breakdown
            lang_response = github_get(data["languages_url"])
            languages: dict[str, int] = (
                lang_response.json() if lang_response.status_code == 200 else {}
            )

            # Contributors list
            contrib_response = github_get(data["contributors_url"])
            contributors: list[dict] = (
                contrib_response.json() if contrib_response.status_code == 200 else []
            )
            contributor_count = len(contributors)

            # Issues list
            issues_response = github_get(
                f"https://api.github.com/repos/{owner}/{repo}/issues"
            )
            issues_data: list[dict] = (
                issues_response.json() if issues_response.status_code == 200 else []
            )

        # ── 3. Core stats ──────────────────────────────────────────────────────
        stars         = data.get("stargazers_count", 0)
        forks         = data.get("forks_count", 0)
        open_issues   = data.get("open_issues_count", 0)
        repo_language = data.get("language") or ""
        topics        = data.get("topics", [])
        description   = data.get("description", "")
        last_updated  = data["updated_at"][:10]

        created_date  = datetime.strptime(data["created_at"][:10], "%Y-%m-%d")
        repo_age      = datetime.now().year - created_date.year

        # ── 4. Computed scores ─────────────────────────────────────────────────
        activity_score = compute_activity_score(stars, forks, contributor_count, open_issues)
        health_score   = compute_health_score(stars, open_issues, bool(description), bool(repo_language))
        difficulty     = compute_difficulty(stars, open_issues)
        match_score, match_reasons = compute_skill_match(repo_language, topics, skills)
        readiness_score = int(match_score * 0.5 + health_score * 0.3 + activity_score * 0.2)
        overall_score   = (health_score + activity_score + match_score) / 3
        repo_rating, _  = compute_repo_rating(overall_score)

        if activity_score >= 75:
            activity_status = "🔥 Highly Active"
        elif activity_score >= 50:
            activity_status = "🟡 Moderately Active"
        else:
            activity_status = "🔴 Low Activity"

        # ── 5. Process issues ──────────────────────────────────────────────────
        issue_titles: list[str] = []
        best_issues:  list[dict] = []
        beginner_count = 0

        for issue in issues_data:
            # GitHub returns PRs in /issues — skip them
            if "pull_request" in issue:
                continue
            title_lower = issue["title"].lower()
            issue_titles.append(issue["title"])
            if any(kw in title_lower for kw in BEGINNER_KEYWORDS):
                beginner_count += 1
                best_issues.append({"title": issue["title"], "url": issue["html_url"]})

        # ── 6. DISPLAY ─────────────────────────────────────────────────────────
        st.success("✅ Repository found!")
        st.divider()

        # --- Repository header ---
        st.subheader(f"📦 {data['name']}")
        st.write(description or "_No description provided._")
        st.link_button("🔗 Open on GitHub", data["html_url"])
        st.write(f"📅 Last Updated: **{last_updated}** &nbsp;|&nbsp; 🕒 Repository Age: **{repo_age} year(s)**")

        st.divider()

        # ── ROW 1: Primary metrics ─────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⭐ Stars", f"{stars:,}")
        with col2:
            st.metric("🍴 Forks", f"{forks:,}")
        with col3:
            st.metric("🐛 Open Issues", f"{open_issues:,}")
        with col4:
            st.metric("👥 Contributors", f"{contributor_count:,}")

        # ── ROW 2: Score metrics ───────────────────────────────────────────────
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("🏥 Health Score", f"{health_score}/100")
        with col6:
            st.metric("⚡ Activity Score", f"{activity_score}/100")
        with col7:
            st.metric("🎯 Skill Match", f"{match_score}%")
        with col8:
            st.metric("🚀 Readiness", f"{readiness_score}%")

        # ── ROW 3: Qualitative metrics ─────────────────────────────────────────
        col9, col10, col11 = st.columns(3)
        with col9:
            st.metric("🏆 Difficulty", difficulty.split(" ", 1)[-1])
        with col10:
            st.metric("📊 Activity", activity_status.split(" ", 1)[-1])
        with col11:
            st.metric("🌟 Rating", repo_rating.split(" ", 1)[-1])

        st.divider()

        # ── REPOSITORY HEALTH BAR ─────────────────────────────────────────────
        st.write("### 📊 Repository Health")
        st.progress(health_score / 100, text=f"Health Score: {health_score}/100")

        # Readiness message (no duplicates, no generic "❌ Not Ready Yet")
        readiness_msg, readiness_level = readiness_label(readiness_score)
        if readiness_level == "success":
            st.success(readiness_msg)
        elif readiness_level == "warning":
            st.warning(readiness_msg)
        else:
            st.error(readiness_msg)

        st.divider()

        # ── FEATURE 1: CONTRIBUTOR ACTIVITY CHART ─────────────────────────────
        st.write("### 📈 Repository Activity Overview")

        chart_df = pd.DataFrame(
            {
                "Metric": ["⭐ Stars", "🍴 Forks", "👥 Contributors", "🐛 Open Issues"],
                "Count": [
                    max(stars, 0),
                    max(forks, 0),
                    max(contributor_count, 0),
                    max(open_issues, 0),
                ],
            }
        ).set_index("Metric")

        st.bar_chart(chart_df, height=300, use_container_width=True)

        st.divider()

        # ── FEATURE 2: TOPIC-BASED SKILL MATCHING ─────────────────────────────
        st.write("### 🎯 Why This Matches You")

        if skills:
            # Visual score bar
            st.progress(match_score / 100, text=f"Skill Match Score: {match_score}%")
            st.write("")

            if match_reasons:
                for reason in match_reasons:
                    st.markdown(f"- {reason}")
            else:
                st.info("No skill overlap detected. Try selecting skills related to this repository's tech stack.")

            # Final verdict
            if match_score >= 70:
                st.success(f"🟢 Strong match ({match_score}%) — this project suits your skills well.")
            elif match_score >= 40:
                st.warning(f"🟡 Moderate match ({match_score}%) — you have some relevant skills.")
            else:
                st.error(f"🔴 Low match ({match_score}%) — consider building up related skills first.")
        else:
            st.info("Select your skills above to see a personalised match analysis.")

        st.divider()

        # ── TOPICS ────────────────────────────────────────────────────────────
        if topics:
            st.write("### 🏷️ Topics")
            # Display topics as inline badges
            badge_row = "  ".join(f"`{t}`" for t in topics[:15])
            st.markdown(badge_row)
            st.write("")

        # ── LANGUAGE BREAKDOWN ────────────────────────────────────────────────
        if languages:
            st.write("### 💻 Language Breakdown")
            total_bytes = sum(languages.values())
            for lang_name, byte_count in sorted(languages.items(), key=lambda x: -x[1]):
                pct = round((byte_count / total_bytes) * 100, 1)
                st.progress(pct / 100, text=f"{lang_name}: {pct}%")

        st.divider()

        # ── TOP CONTRIBUTORS ─────────────────────────────────────────────────
        st.write("### 👥 Top Contributors")
        if contributors:
            c_head1, c_head2 = st.columns([4, 1])
            with c_head1:
                st.caption("Username")
            with c_head2:
                st.caption("Commits")
            for contributor in contributors[:5]:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"[@{contributor['login']}](https://github.com/{contributor['login']})")
                with c2:
                    st.write(contributor.get("contributions", "—"))
        else:
            st.info("Contributor data unavailable.")

        st.divider()

        # ── ISSUE FILTER & LIST ───────────────────────────────────────────────
        st.write("### 🐛 Issues")
        issue_filter = st.selectbox(
            "Filter Issues",
            ["All Issues", "Beginner Issues", "Documentation Issues"],
            label_visibility="collapsed",
        )

        # ── RECOMMENDED FIRST ISSUES ─────────────────────────────────────────
        st.write("### 🎯 Recommended First Issues")
        if best_issues:
            for issue in best_issues[:5]:
                st.link_button(issue["title"], issue["url"])
        else:
            st.info("No beginner-friendly issues found in the latest batch.")

        # Issue list inside expander
        with st.expander("📋 View Issues", expanded=False):
            displayed = 0
            for issue in issues_data:
                if "pull_request" in issue:
                    continue
                title_lower = issue["title"].lower()

                show = False
                if issue_filter == "All Issues":
                    show = True
                elif issue_filter == "Beginner Issues":
                    show = any(kw in title_lower for kw in BEGINNER_KEYWORDS)
                elif issue_filter == "Documentation Issues":
                    show = "doc" in title_lower or "readme" in title_lower

                if show:
                    st.link_button(issue["title"], issue["html_url"])
                    displayed += 1

                if displayed >= 10:
                    break

            if displayed == 0:
                st.info("No issues match the selected filter.")

        st.divider()

        # ── README PREVIEW ───────────────────────────────────────────────────
        if readme_text:
            st.write("### 📖 README Preview")
            with st.expander("View README", expanded=False):
                # Render up to 2000 chars as Markdown for better formatting
                st.markdown(readme_text[:2000])
                if len(readme_text) >= 2000:
                    st.caption("_README truncated — open the repository for the full version._")

        st.divider()

        # ── AI TABS ──────────────────────────────────────────────────────────
        # Tab 1 — Gemini-generated overview (replaces old static summary)
        # Tab 2 — Contribution roadmap
        # Tab 3 — Best contribution recommendation

        tab1, tab2, tab3 = st.tabs(["📋 Overview", "🗺️ Roadmap", "🎯 Recommendation"])

        # --- Tab 1: AI Summary ---
        with tab1:
            st.write("#### 🤖 AI-Generated Repository Summary")
            with st.spinner("Asking Gemini to analyse this repository…"):
                try:
                    ai_summary = generate_ai_summary(
                        repo_name=data["name"],
                        description=description,
                        language=repo_language or "Mixed",
                        stars=stars,
                        forks=forks,
                        topics=topics,
                        recent_issue_titles=issue_titles[:10],
                        user_skills=skills,
                    )
                    st.markdown(ai_summary)
                except Exception as gemini_err:
                    st.warning(
                        f"Could not generate AI summary at this time: {gemini_err}\n\n"
                        f"**Basic Info** — **{data['name']}** | "
                        f"Language: {repo_language or 'Mixed'} | "
                        f"Stars: {stars:,} | Forks: {forks:,}"
                    )

        # --- Tab 2: Roadmap ---
        with tab2:
            st.write("#### 🗺️ 5-Day Contribution Roadmap")
            if st.button("Generate Roadmap", key="roadmap_btn"):
                roadmap_prompt = f"""
You are an open-source mentor creating a practical contribution roadmap.

Repository: {data['name']}
Description: {description or 'N/A'}
Primary Language: {repo_language or 'Mixed'}
User Skills: {', '.join(skills) if skills else 'Not specified'}
Topics: {', '.join(topics) if topics else 'None'}

Create a clear, practical 5-day plan for making a first contribution to this repository.
Each day should have a specific, actionable goal. Include concrete steps, not vague advice.

Format strictly as:
**Day 1:** ...
**Day 2:** ...
**Day 3:** ...
**Day 4:** ...
**Day 5:** ...

After the plan, add a short "💡 Tips" section with 2–3 practical tips.
"""
                with st.spinner("Building your roadmap…"):
                    try:
                        roadmap_response = model.generate_content(roadmap_prompt)
                        st.success("Here's your personalised 5-day roadmap:")
                        st.markdown(roadmap_response.text)
                    except Exception as gemini_err:
                        st.error(f"Could not generate roadmap: {gemini_err}")

        # --- Tab 3: Contribution Recommendation ---
        with tab3:
            st.write("#### 🎯 Best Contribution Recommendation")
            if st.button("Find Best Contribution", key="rec_btn"):
                issues_block = (
                    "\n".join(f"- {t}" for t in issue_titles[:15])
                    if issue_titles
                    else "No recent issues available."
                )
                recommendation_prompt = f"""
You are an expert open-source mentor.

Repository: {data['name']}
Description: {description or 'N/A'}
Primary Language: {repo_language or 'Mixed'}
Topics: {', '.join(topics) if topics else 'None'}
Stars: {stars:,} | Forks: {forks:,} | Open Issues: {open_issues:,}
User Skills: {', '.join(skills) if skills else 'Not specified'}

Recent Issues:
{issues_block}

Recommend the SINGLE BEST contribution opportunity for this user.

Structure your response with these exact headings:
### 🏷️ Recommended Task
### 🤔 Why This Matches Your Skills
### 📊 Expected Difficulty
### ⏱️ Estimated Time
### 🚀 First Step

Be specific and encouraging. Keep each section concise (1–3 sentences).
"""
                with st.spinner("Finding your best contribution opportunity…"):
                    try:
                        rec_response = model.generate_content(recommendation_prompt)
                        st.markdown(rec_response.text)
                    except Exception as gemini_err:
                        st.error(f"Could not generate recommendation: {gemini_err}")

    except ValueError as ve:
        st.error(f"❌ {ve}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Network error — please check your internet connection and try again.")
    except requests.exceptions.Timeout:
        st.error("❌ The request timed out. GitHub API may be slow — please try again.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")