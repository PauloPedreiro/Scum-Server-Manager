# Contributing to Scum Server Manager (SSM 3.0)

First off, thank you for considering contributing to **Scum Server Manager**! 🎉
It people like you that make SSM an incredible tool for server owners and the entire SCUM community.

Please take a moment to review this document in order to make the contribution process easy and effective for everyone involved.

---

## 📜 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainers.

---

## 🚀 How Can I Contribute?

### 1. Reporting Bugs
Before creating a bug report, please check existing [Issues](https://github.com/PauloPedreiro/Scum-Server-Manager/issues) to see if the problem has already been reported.

When filing a bug report, please include:
* A clear, descriptive title.
* Steps to reproduce the behavior.
* Expected vs actual behavior.
* Relevant log snippets (make sure to **redact all passwords, tokens, and webhooks**!).
* Your OS, Python version, Node.js version, and SSM version.

### 2. Suggesting Enhancements
Feature requests are always welcome!
* Use the GitHub Issue tracker.
* Describe the problem you are trying to solve and how the suggested feature would address it.
* If applicable, provide mockups or examples of how the feature would look in the Web Dashboard or in-game chat.

### 3. Submitting Code (Pull Requests)

#### Step 1: Fork and Clone
```bash
git clone https://github.com/<your-username>/Scum-Server-Manager.git
cd Scum-Server-Manager
```

#### Step 2: Create a Feature Branch
Always create your branch from `main`:
```bash
git checkout -b feat/your-feature-name
# or for bugfixes:
git checkout -b fix/issue-description
```

#### Step 3: Local Setup

##### Backend (Python)
```bash
cd Backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
pip install -r requirements.txt

# Run backend
python main.py
```

##### Frontend (React / Vite)
```bash
cd Frontend
npm install
npm run dev
```

#### Step 4: Coding Standards & Rules of Thumb
* **Never commit secrets or live databases**: Keep `config.json`, `webhooks.json`, and `*.db` in `.gitignore`.
* **RCON Safety**:
  * Always route game commands through `RconQueueManager`.
  * Set appropriate delays (`delay_after`) to prevent packet loss.
  * Sanitise player inputs to prevent newline command injection.
* **SQLite Concurrency**: Protect multi-thread writes using thread locks (`threading.Lock`) to prevent `"database is locked"` errors.
* **TypeScript & React**: Follow standard ESLint rules, use strong types, and maintain reusable UI components.

#### Step 5: Commit Style
We encourage using [Conventional Commits](https://www.conventionalcommits.org/):
* `feat:` A new feature
* `fix:` A bug fix
* `docs:` Documentation changes only
* `style:` Formatting, missing semi-colons, etc (no functional code changes)
* `refactor:` Refactoring production code without changing behavior
* `test:` Adding or refactoring tests
* `chore:` Updating build tasks, package manager configs, etc.

*Example:* `feat(kill-feed): add custom chat color selection`

#### Step 6: Open a Pull Request (PR)
1. Push your branch to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request against the `main` branch of `PauloPedreiro/Scum-Server-Manager`.
3. Provide a clear description of the changes, referencing any related issues (`Fixes #12`).
4. Wait for code review from the maintainers.

---

## 💬 Community & Questions

Need help or want to discuss ideas before coding?
* Join our official [Discord Community](https://discord.gg/EHwQTKWAtv).
* Ask questions in the `#development` or `#support` channels.

Thank you for contributing to **Scum Server Manager**! 🎮
