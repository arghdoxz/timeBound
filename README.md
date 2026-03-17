# TimeBound

TimeBound is a cross-platform academic task manager built with Python and Kivy. It helps students organize assignments into daily subtasks, schedule reminders, and reduce distractions with focus-mode app blocking.

## Overview

TimeBound was designed to support academic productivity by turning large tasks into smaller daily actions. The app includes task planning, optional AI-assisted breakdowns, reminder scheduling, and focus tools for minimizing distractions during study sessions.

## Features

- Create tasks with deadlines
- Automatically generate daily subtasks
- Optional AI-powered task breakdown using Google Gemini
- Schedule reminder times for each subtask
- Track subtask completion progress
- Focus Mode with app-blocking support
- Local offline data storage using JSON
- Desktop support and Android APK packaging

## Built With

- Python
- Kivy 2.2.1
- Plyer
- Pyjnius
- Psutil
- Google Gemini API
- Buildozer
- Docker

## Project Structure

- `main.py` – main application source code
- `buildozer.spec` – Android build configuration
- `timebound_data.json` – local data storage file generated at runtime
- `icon.jpg` – app icon
- `presplash.jpg` – splash screen image

## Installation

### Desktop

Create a virtual environment and install the required packages:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install kivy==2.2.1 plyer google-generativeai certifi psutil
