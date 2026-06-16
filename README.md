# PageSpeed Track & Audit Engine
A synchronous web-performance monitoring tool built with Django and MySQL. It audits URLs against the Google PageSpeed Insights API, parses Core Web Vitals, and stores historical telemetry for frontend visualization.

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
* **Python 3.10+**
* **MySQL Server** (and optionally MySQL Workbench)
* **Git**

---

## Local Setup Instructions

**1. Clone the repository**
```bash
git clone `https://github.com/prxcode/pagespeed_engine.git`
cd pagespeed_engine
```
- Create Virtual Environment: `python -m venv .venv`
- For windows:  `.\.venv\Scripts\Activate.ps1 `
- For mac/linux: `source .venv/bin/activate`
- Install requirements: `pip install -r requirements.txt`
- Create ".env" file, note the format should look like .env.example just change parameters
- Apply the database schema to your local MySQL instance: `python manage.py migrate`
- Follow cmds from cmds.sql to view the table and data
- Start server: `python manage.py runserver`
- To check whether server is running or not go to web browser and enter http://127.0.0.1:8000/ as URL.



## Git Workflow & Contribution Guide
To maintain a stable codebase, we use a standard Feature Branch workflow. Do not push directly to the main branch.

#### 1. Create a Feature Branch
```bash
# 1. Go back to the main branch
git checkout main

# 2. Pull main 
git pull origin main

# 3. Create a fresh branch for next task
git checkout -b <user>/<new-task-name>
```

#### 2. Commit your changes
```bash
git add .
git commit -m "style: Add Chart.js rendering for historical performance trends"
```


Use **Conventional Commits**, They make commit history cleaner and help with changelogs and versioning.

```bash
| Prefix      | Meaning                                      | Example                                      |
| ----------- | -------------------------------------------- | -------------------------------------------- |
| `feat:`     | New feature                                  | `feat: add <example>`                        |
| `fix:`      | Bug fix                                      | `fix: resolve <example> issue`               |
| `docs:`     | Documentation only                           | `docs: update README setup instructions`     |
| `style:`    | Formatting, whitespace, no code changes      | `style: format code with black`              |
| `refactor:` | Code restructuring without changing behavior | `refactor: simplify <example> logic`         |
| `perf:`     | Performance improvement                      | `perf: optimize <example>`                   |
| `test:`     | Add or modify tests                          | `test: add unit tests for <example>`         |
| `build:`    | Build system or dependencies                 | `build: upgrade <example> dependency`        |
| `ci:`       | CI/CD changes                                | `ci: add GitHub Actions workflow`            |
| `chore:`    | Misc maintenance                             | `chore: update gitignore`                    |
| `revert:`   | Revert a previous commit                     | `revert: revert <example> changes`           |
| `init:`     | Initial project setup                        | `init: create aegis project structure`       |
| `merge:`    | Branch merge                                 | `merge: combine feature branch into main`    |
| `security:` | Security-related fix                         | `security: sanitize user input handling`     |
| `hotfix:`   | Urgent production fix                        | `hotfix: fix application crash on startup`   |
| `release:`  | Release version preparation                  | `release: prepare v1.0.0 for deployment`     |
```


#### 3. Push and Open a Pull Request (PR)
```bash
git push origin <feature>/<your-feature-name>
```
Open: `https://github.com/prxcode/pagespeed_engine` and click "SEND PR"

#### 4. Once you all are done with sending PR and your PR is merged by prxcode
```bash
# 1. Go back to the main branch
git checkout main

# 2. Pull main latest code 
git pull origin main

# 3. Delete the old local branch
git branch -d <user>/<fixing-url-input>

# 4. Create a fresh branch for next task
git checkout -b <user>/<new-task-name>
```

#### 5. To pull changes from main branch
To pull the latest updates from the remote `main` branch into your local repository:

If you're currently on `main`

```bash
git checkout main
git pull origin main
```

This switches to `main` and downloads + merges the latest changes from the remote.

Then switch back to your feature branch:

```bash
git checkout <user>/<url-fix>
```

Merge `main` into it:

```bash
git rebase main
```

Done, now to check what branch you're on [OPTIONAL]

```bash
git branch
```

The current branch will have a `*` next to it.

To see if you're behind the remote [OPTIONAL]

```bash
git fetch origin
git status
```

#### 6. if you want to stash changes which you are working on and then pull requests
If you just want to sync main first:
```bash
git stash
```

Now your working directory is clean.
Then:
```bash
git pull origin main
```
or:
```bash
git rebase main
```
Then bring your changes back:
```bash
git stash pop
```
#### 7. If you don't want the changes which you are working on and want to overwrite with main
This deletes current changes
```bash
git reset --hard
```
If you also want to remove untracked files (like new migration files):
```bash
git clean -fd
```

Now you can overwrite
```bash
git pull origin main
```
#### 8. Review and Merge [ONLY FOR PRIYANSHU]
```bash
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```
