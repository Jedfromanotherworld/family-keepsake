# GitHub, push, pull and pull requests in VS Code

## Open your existing repository in VS Code

Your private repository is https://github.com/Jedfromanotherworld/family-keepsake.

1. Install Git and sign in to GitHub in VS Code when prompted.
2. Press Ctrl+Shift+P, choose **Git: Clone**, and enter the repository URL.
3. Choose a local folder and select **Open** after cloning.
4. Follow README.md to install Python dependencies and initialize your local database.

Or use the terminal:

```bash
git clone https://github.com/Jedfromanotherworld/family-keepsake.git
cd family-keepsake
code .
```

Review `git status` before committing. Never commit `data/`, private photos, passwords, `.env`, or backups. GitHub authentication may open your browser; never put an access token into source code or a remote URL.

## Each change: branch → commit → push → PR

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/change-family-title
```

Edit the files in VS Code. Test the app. Then:

```bash
python -m unittest discover -s tests -v
git add .
git commit -m "Update family archive title"
git push -u origin feature/change-family-title
```

On GitHub, click **Compare & pull request**. Set base to `main` and compare to your feature branch. Describe the change, wait for the automated checks, review it, and merge it. You can also use Microsoft's **GitHub Pull Requests** VS Code extension.

After merging:

```bash
git switch main
git pull --ff-only origin main
git branch -d feature/change-family-title
```

If Git refuses to switch because of local edits, commit or stash them first. Do not use force-push or discard work merely to bypass an error.

A **push** sends commits to GitHub. A **pull** brings commits into your local checkout. A **pull request** asks to review and merge one branch into another. None of these commands back up uploaded family media or automatically update your running server in this project.

Official guides:
- https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request
- https://code.visualstudio.com/docs/sourcecontrol/github
