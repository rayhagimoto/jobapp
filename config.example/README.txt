JobApp Example Configuration Files and Structure
===============================================

This directory now includes example subdirectories and files to illustrate the recommended layout for your personal configuration under:
    ~/.config/jobapp/

**All files here are safe, non-secret examples. Do NOT use real credentials or secrets in this directory.**

Example structure:

config.example/
├── config/
│   ├── default.yaml
│   ├── resume_writer.yaml
│   └── search.yaml
├── auth/
│   ├── gspread_credentials.example.json
│   └── linkedin_auth.example.json
├── secrets/
│   └── .env.example
├── data/
│   └── user/
│       ├── experiences.example.md
│       └── resume.example.yaml

**Instructions:**
- Copy the example YAML files from config.example/config/ to ~/.config/jobapp/config/ and edit as needed.
- Place your real API keys in ~/.config/jobapp/secrets/.env (use .env.example as a template).
- Place your Google Sheets and LinkedIn credentials in ~/.config/jobapp/auth/ (use the .example.json files as templates).
- Place your resume and experience data in ~/.config/jobapp/data/user/ (use the .example files as templates).

**DO NOT commit your real credentials, secrets, or user data to any public repository.**

This example directory does NOT include any real credentials, .env files, or user data—only example files and templates. 