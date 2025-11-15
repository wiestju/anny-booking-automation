# 📚 KIT Anny Booking Automation

This Python project automates booking of study spaces or resources via the [anny.eu](https://anny.eu) platform used by the KIT (Karlsruhe Institute of Technology) library system. It logs in automatically using KIT SAML SSO, searches for available slots, and makes bookings without user interaction — ideal for recurring reservations.

---

## ⚙️ Features

- 🔐 Automatic KIT login via SAML SSO  
- 📆 Configurable 3-days-ahead reservation window  
- 🔎 Auto-detection of available time slots  
- ⏳ Pre-login shortly before midnight to instantly book a slot at 00:00  
- 🛠️ Clean and modular object-oriented codebase  
- 🔁 Fully automated execution using [cron-job.org](https://cron-job.org) + GitHub API  
- 📦 Easy to extend and maintain  

---

## 🗂️ Project Structure

```
anny_booking/
├── .env                         # Credentials (excluded from version control)
├── main.py                      # Entry point for script execution
├── requirements.txt             # Python dependencies
│
├── auth/
│   └── session.py               # AnnySession class (login logic)
│
├── booking/
│   └── client.py                # BookingClient class (resource booking)
│
├── config/
│   └── constants.py             # API URLs and shared constants
│
├── utils/
│   └── helpers.py               # Utility functions
│
└── .github/
    └── workflows/
        └── schedule.yml         # GitHub Actions workflow (manual trigger)
```

---

## 🚀 Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/anny-booking-automation.git  
cd anny-booking-automation
```

### 2. Set up a Python virtual environment

```bash
python3 -m venv venv  
source venv/bin/activate  
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root of the project:

```
USERNAME=your_kit_username  
PASSWORD=your_kit_password
```

> 🔒 Never commit this file to version control!

---

## ⏱️ Automated Execution via cron-job.org + GitHub API

To maximize booking success, the script is triggered **two minutes before midnight** (e.g., 23:58).  
It logs in to the KIT SAML SSO in advance, keeps the session alive, and **waits internally until exactly 00:00** to instantly book the best available slot as soon as new reservations open.

The trigger is handled by:

- `cron-job.org` for precise scheduling (e.g., 23:58 Europe/Berlin)  
- GitHub Actions to run the actual script with credentials passed via GitHub Secrets  

### Why not just use `on: schedule`?

GitHub Actions only supports fixed cron expressions (e.g., once per hour) and does **not** allow more frequent triggers like every 5 or 10 minutes.  
Additionally, it suffers from two major issues:

- ⏳ **Queue delay**: Workflows triggered via GitHub's `schedule` event are sometimes delayed by several minutes due to internal queue congestion. This can cause the booking script to miss the optimal reservation window.  
- 🕒 **Timezone limitations**: GitHub's cron system uses UTC without native timezone support. That means you need to manually convert your desired local time (e.g. Europe/Berlin) and keep adjusting for daylight saving time changes.  

For these reasons, we use [cron-job.org](https://cron-job.org), which offers:

- ✅ Precise minute-level scheduling  
- ✅ Native timezone selection (e.g. Europe/Berlin)  
- ✅ Immediate webhook execution with no delay  

This ensures your booking script runs exactly when needed — already logged in and ready to act at 00:00.

---

### How it works

1. `cron-job.org` triggers the GitHub Actions workflow at **23:58** (Europe/Berlin).  
2. The script logs in via KIT SAML SSO and maintains an active session.  
3. It waits internally until **00:00**.  
4. As soon as new booking slots are released, it instantly reserves the first suitable slot.  

---

### Setup steps

1. Set up a cron job on `cron-job.org` that sends a POST request to:

```
https://api.github.com/repos/your-username/anny-booking-automation/actions/workflows/schedule.yml/dispatches
```

2. Include the following JSON payload:

```json
{"ref": "main"}
```

3. Add this header:

```
Authorization: Bearer YOUR_GITHUB_PERSONAL_ACCESS_TOKEN  
Content-Type: application/json  
Accept: application/vnd.github.v3+json
```

4. Your GitHub workflow (`.github/workflows/schedule.yml`) listens for this event:

```yaml
name: Daily Library Reservation Automation

on:
  workflow_dispatch:

jobs:
  run-script:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run script
        env:
          USERNAME: ${{ secrets.USERNAME }}
          PASSWORD: ${{ secrets.PASSWORD }}
        run: |
          python main.py
```

> 💡 Store your KIT credentials securely as [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets): `USERNAME` and `PASSWORD`.

---

## 🤝 Contributing

Pull requests are welcome! Feel free to open an issue or suggest features or improvements.

---

## 📎 Related Tools

- [cron-job.org](https://cron-job.org)  
- [GitHub Actions](https://github.com/features/actions)  
- [anny.eu](https://anny.eu)
