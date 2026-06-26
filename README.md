🚀 OSS Mentor AI

OSS Mentor AI is a project I built to make open-source contributions less intimidating for beginners.

When I first started exploring open source, I often found myself asking:

* Which repository should I contribute to?
* Is this project too difficult for me?
* Where do I even start?
* What issue should I pick?

OSS Mentor AI tries to answer those questions by combining GitHub repository analysis with AI-generated guidance.

⸻

💡 What It Does

Simply enter a GitHub repository URL and select your skills.

The application will:

* Analyze the repository
* Evaluate its activity and health
* Check how well it matches your skills
* Identify beginner-friendly opportunities
* Generate AI-powered summaries
* Create a contribution roadmap
* Recommend a suitable first contribution

⸻

✨ Features

Repository Analysis

* Stars, forks, issues, and contributor statistics
* Repository health score
* Activity score
* Difficulty assessment
* Repository rating

Smart Skill Matching

* Matches repository technologies with your skills
* Explains why a project is a good fit
* Generates a contribution readiness score

AI-Powered Guidance

Using Google Gemini AI:

* Repository summaries
* Personalized contribution roadmaps
* Contribution recommendations
* Beginner-friendly guidance

Open Source Discovery

* Beginner issue detection
* Language breakdown
* README preview
* Contributor insights

⸻

🛠️ Tech Stack

* Python
* Streamlit
* GitHub REST API
* Google Gemini API
* Pandas
* Requests
* Python Dotenv

⸻

⚙️ How It Works

1. Enter a GitHub repository URL.
2. Select your skills.
3. The application fetches repository data using the GitHub API.
4. Repository metrics are analyzed.
5. Gemini AI generates insights and recommendations.
6. You receive a personalized roadmap to start contributing.

⸻

🚀 Running Locally

Clone the repository:

git clone https://github.com/akkusochill/oss-mentor-ai.git
cd oss-mentor-ai

Create a virtual environment:

python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create a .env file:

GEMINI_API_KEY=your_api_key_here

Run the app:

streamlit run app.py

⸻

🎯 Why I Built This

As a student trying to get involved in open source, I realized that finding the right project is often harder than actually contributing.

This project was built to help developers spend less time searching and more time building.

⸻

🔮 Future Improvements

* GitHub OAuth login
* PDF contribution reports
* Repository comparison tool
* Better issue recommendation system
* Contribution tracking dashboard

⸻

👩‍💻 About Me

I’m Akanksha, a Computer Science Engineering student who enjoys building projects with AI, developer tools, and automation.

If you have suggestions or feedback, feel free to connect or open an issue in the repository.

⭐ If you found this project useful, consider giving it a star!
