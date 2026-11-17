# Contributing to UseWorldview

Thank you for your interest in contributing to **UseWorldview**! We are building an open, transparent, and AI-powered synthetic user research platform for product and design teams worldwide.

Whether you're fixing a bug, improving the autonomous browser agent loop, expanding the psychographic worldview engine, or enhancing documentation — your contributions are welcome.

---

## 📜 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [How Can I Contribute?](#-how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Pull Requests](#pull-requests)
- [Development Setup](#-development-setup)
  - [Backend Setup (FastAPI & Playwright)](#backend-setup)
  - [Frontend Setup (Next.js 16)](#frontend-setup)
- [Git Conventions & Commit Standards](#-git-conventions--commit-standards)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Community & Communication](#-community--communication)

---

## 🤝 Code of Conduct

This project adheres to the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [abhinavsharma8750@gmail.com](mailto:abhinavsharma8750@gmail.com).

---

## 💡 How Can I Contribute?

### Reporting Bugs

Before creating an issue, please check existing GitHub issues to make sure the problem hasn't already been reported.

When creating an issue, please include:
- A descriptive title.
- Clear steps to reproduce the behavior.
- Expected vs. actual behavior.
- Screenshots, console logs, or agent session errors if applicable.
- Environment details (OS, Python version, Node.js version, browser).

### Suggesting Features

We welcome ideas that enhance synthetic persona realism, browser agent exploration capabilities, or dashboard telemetry!

Please open a feature request issue with:
- The problem your proposal solves.
- A detailed description of the suggested enhancement.
- Any potential alternatives or trade-offs considered.

### Pull Requests

1. **Fork the repo** and create your branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```
2. **Implement your changes**: Keep commits focused and atomic.
3. **Write/update tests** to cover your changes.
4. **Verify linting & builds** before pushing.
5. **Open a Pull Request** against the `main` branch with a clear description of what changed.

---

## 🛠 Development Setup

### Monorepo Architecture
UseWorldview is organized into two primary applications:
- [`backend/`](backend/): Python 3.11+ FastAPI service, headless Playwright runner, and async worker.
- [`frontend/`](frontend/): Next.js 16 (App Router), React 19, and Tailwind CSS v4.

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy and configure environment
cp .env.example .env
# Fill in your Supabase credentials and at least one LLM key

# Run tests
pytest

# Start backend server (unified API + worker)
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY

# Run linter
npm run lint

# Start Next.js dev server
npm run dev
```

---

## 📝 Git Conventions & Commit Standards

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature for users or agents
- `fix:` A bug fix
- `docs:` Documentation-only changes
- `style:` Changes that do not affect the meaning of code (formatting, missing semi-colons)
- `refactor:` A code change that neither fixes a bug nor adds a feature
- `perf:` A code change that improves performance
- `test:` Adding missing tests or correcting existing tests
- `chore:` Changes to build process, dependency updates, or tools

*Example:* `feat(agent): add support for handling nested iframe menus`

---

## 🧪 Testing & Quality Assurance

All PRs should maintain high code standards:

- **Backend**:
  - Keep types clean with Pydantic v2.
  - Run `pytest -v` to ensure all tests pass.
- **Frontend**:
  - Run `npm run lint` and verify zero ESLint errors.
  - Ensure `npm run build` succeeds without type errors.

---

## 💬 Community & Communication

Have questions or want to discuss ideas?
- Open a GitHub Discussion or Issue.
- Reach out to the maintainers at [abhinavsharma8750@gmail.com](mailto:abhinavsharma8750@gmail.com).
