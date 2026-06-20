import streamlit as st
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Create Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")

# App title
st.title("OSS Mentor AI 🚀")

repo_url = st.text_input(
    "Enter a GitHub repository URL",
    placeholder="https://github.com/owner/repo"
)

skills = st.text_input(
    "Your Skills",
    placeholder="Python, Git, SwiftUI, JavaScript"
)


if st.button("Analyze Repository"):

    if not repo_url:
        st.warning("Please enter a repository URL.")
    else:
        try:
            # Extract owner and repo name
            parts = repo_url.strip("/").split("/")

            if len(parts) < 2:
                st.error("Invalid GitHub repository URL.")
                st.stop()

            owner = parts[-2]
            repo = parts[-1]

            # Repository API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url)

            if response.status_code != 200:
                st.error("Repository not found.")
                st.stop()

            data = response.json()

            st.success("Repository found!")

            # Repository Information
            st.write("## Repository Information")

            st.write(f"**Name:** {data['name']}")
            st.write(f"**Description:** {data['description']}")
            st.write(f"**Language:** {data['language']}")
            st.write(f"**Stars:** {data['stargazers_count']}")
            st.write(f"**Open Issues:** {data['open_issues_count']}")

            # Recent Issues
            issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            issues_response = requests.get(issues_url)

            issue_titles = []

            if issues_response.status_code == 200:
                issues_data = issues_response.json()

                st.write("## Recent Issues")

                issue_count = 0

                for issue in issues_data:
                    if "pull_request" not in issue:
                        issue_titles.append(issue["title"])

                        st.write(
                            f"- [{issue['title']}]({issue['html_url']})"
                        )

                        issue_count += 1

                    if issue_count >= 5:
                        break

            # Difficulty Analysis
            stars = data["stargazers_count"]
            open_issues = data["open_issues_count"]

            if stars > 500 and open_issues < 50:
                difficulty = "🟢 Beginner Friendly"
            elif stars > 100:
                difficulty = "🟡 Intermediate"
            else:
                difficulty = "🔴 Advanced"

            st.write("## Contribution Difficulty")
            st.success(difficulty)

            # AI Summary
            st.write("## 🤖 AI Repository Summary")
            st.write("## 🗺️ Contribution Roadmap")

            prompt = f"""
You are an expert open-source mentor.

Repository Name:
{data['name']}

Description:
{data['description']}

Primary Language:
{data['language']}

Stars:
{data['stargazers_count']}

Open Issues:
{data['open_issues_count']}

Open Issues:
{data['open_issues_count']}

Recent Issues:
{chr(10).join(issue_titles)}


Explain:
1. What this repository does.
2. Whether it is beginner friendly.
3. What kind of contributions a beginner can make.
4. Suggested first contribution.
5. Difficulty level.

Keep the response short, practical, and beginner-friendly.
"""

            ai_response = model.generate_content(prompt)

            st.info(ai_response.text)

            # Roadmap Section

            st.write("## 🗺️ Contribution Roadmap")
            roadmap_prompt = f"""
            You are an open-source mentor.
            Repository:
            {data['name']}
            User Skills:
            {skills}
            Create a practical 5-day roadmap for making a first contribution.
            Format:
            Day 1:
            ...
            Day 2:

            ...

            Day 3:
            ...
            Day 4:
            ...

            Day 5:
            ...

            """

            roadmap_response = model.generate_content(

                roadmap_prompt

            )

            st.success(roadmap_response.text)


            st.write("## 🎯 Best Contribution Recommendation")

            recommendation_prompt = f"""
            You are an expert open-source mentor.

            Repository:
            {data['name']}
            Description:
            {data['description']}
            User Skills:
            {skills}
            Recent Issues:
            {chr(10).join(issue_titles)}

            Recommend the SINGLE BEST contribution opportunity.

            Explain:
            1. Which issue/task to choose
            2. Why it matches the user's skills
            3. Expected difficulty
            4. Estimated time required
            5. First step to get started

            Keep it concise.
            """
            recommendation_response = model.generate_content(
                recommendation_prompt
            )

            st.warning(recommendation_response.text)


        except Exception as e:
            st.error(f"Error: {e}")