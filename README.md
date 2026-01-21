# Dimagi

### Dimagi Pytest Automation Suite

This repository contains an end-to-end **test automation framework** built using **Python, Pytest, Selenium, and Appium**, with full CI/CD integration using **GitHub Actions**.

The framework supports:
- 🌐 Web automation
- 📱 Mobile automation (BrowserStack)
- 📊 Allure reporting
- 🔁 CI/CD pipelines
- 🔔 Slack notifications
- 🌍 Allure report publishing via GitHub Pages

---

### 📌 Tech Stack

| Tool | Purpose |
|-----|--------|
| Python 3.10 | Programming language |
| Pytest | Test framework |
| Selenium | Web automation |
| Appium | Mobile automation |
| BrowserStack | Cloud mobile testing |
| Allure | Test reporting |
| GitHub Actions | CI/CD |
| Slack | Notifications |

---

### 📂 Project Structure
```
Dimagi/
├── .github/
│ └── workflows/
│
├── .venv/
│
├── app/
│
├── config/
│
├── drivers/
│
├── locators/
│
├── pages/
│ ├── web_pages/
│ └── mobile_pages/
│
├── reports/
│ ├── allure-report/
│ ├── allure-results/
│ └── results.xml
│
├── test_data/
│
├── tests/
│ ├── web_tests/
│ └── mobile_tests/
│
├── utils/
│
├── .gitignore
├── conftest.py
├── pytest.ini
├── README.md
└── requirements.txt
```
---

### 🧠 Framework Design Highlights
- **Page Object Model (POM)** for clean separation of tests and UI logic
- **Pytest fixtures** for driver management and setup/teardown
- **Separate execution flows** for Web and Mobile tests
- **Allure reporting** for detailed test insights
- **CI/CD ready** with GitHub Actions
- **BrowserStack integration** for cloud mobile execution
- **Secure secrets handling** via GitHub Secrets

---

### 📌 Key Directories Explained

| Directory | Purpose                                          |
|---------|--------------------------------------------------|
| `tests/` | Contains all web and mobile test cases           |
| `pages/` | Page Object Model implementations                |
| `locators/`| Element locators for web and mobile tests        |
| `drivers/` | WebDriver and Appium driver setup                |
| `config/` | Environment and capability configurations        |
| `test_data/` | Test data required for web and mobile test cases |
| `reports/` | Allure reports and test artifacts                |
| `utils/` | Reusable helper utilities                        |
| `.github/workflows/` | CI/CD pipeline definitions                       |

---

### ⚙️ Prerequisites

- Python **3.10+**
- Google Chrome (for web tests)
- BrowserStack account (for mobile tests)

---

### 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

### 🔑 Environment Variables
BrowserStack (Required for Mobile Tests)

```bash
macOS / Linux
export BROWSERSTACK_USERNAME=your_username
export BROWSERSTACK_ACCESS_KEY=your_access_key
```

```bash
Windows (PowerShell)
$env:BROWSERSTACK_USERNAME="your_username"
$env:BROWSERSTACK_ACCESS_KEY="your_access_key"
```

### ▶️ Run Tests Locally
Run Web Tests
```
pytest -v tests/web_tests
```

Run Mobile Tests
```
pytest -v tests/mobile_tests
```

### 📊 Allure Reports (Local Execution)
Generate Allure Results
```
pytest -v tests/web_tests --alluredir=reports/web/allure-results
```

Generate HTML Report
```
allure generate reports/web/allure-results -o reports/web-allure-report --clean
```

Open Report
```
allure open reports/web-allure-report
```
⚠️ allure open works only on local machines, not in CI/CD.


### 🚀 CI/CD with GitHub Actions
Trigger Conditions
- Push to main
- Pull request to main

CI Pipeline Includes
- Web tests execution
- Mobile tests execution (BrowserStack)
- Allure report generation
- Slack notifications

### 🔐 GitHub Secrets Configuration
Add secrets under:

Repository → Settings → Secrets and variables → Actions

|Secret Name|Description|
|-----------|-----------|
|BROWSERSTACK_USERNAME|BrowserStack username|
|BROWSERSTACK_ACCESS_KEY|BrowserStack access key|
|SLACK_WEBHOOK_URL|Slack incoming webhook|

### 🔔 Slack Notifications
- Sends notification on every CI run
- Includes job status and workflow link