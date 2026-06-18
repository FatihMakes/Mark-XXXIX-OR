import os
import sys
import json
import re
import subprocess
import shutil
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
STUDIES_DIR = BASE_DIR / "scratch" / "github_studies"

def run_github_updater(repo_url: str) -> str:
    print(f"[GitHub Updater] Received request for repository: {repo_url}")
    
    # Extract repo name
    m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
    if m:
        repo_owner, repo_name = m.group(1), m.group(2)
        repo_name = repo_name.replace(".git", "")
    else:
        # Fallback if it is just a name or name/name
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_owner = "unknown"
        if "/" in repo_url and not repo_url.startswith("http"):
            repo_owner = repo_url.split("/")[0]

    dest_path = STUDIES_DIR / repo_name
    
    # 1. Clone repository
    print(f"[GitHub Updater] Sandbox destination: {dest_path}")
    if dest_path.exists():
        print(f"[GitHub Updater] Folder exists. Removing old version...")
        try:
            shutil.rmtree(dest_path)
        except Exception as e:
            return f"Failed to run GitHub Updater: Cannot clean old directory: {e}"

    os.makedirs(STUDIES_DIR, exist_ok=True)
    
    # Prepare clone command
    if repo_url.startswith("http"):
        clone_url = repo_url
    else:
        clone_url = f"https://github.com/{repo_owner}/{repo_name}.git"

    print(f"[GitHub Updater] Cloned repository from {clone_url}...")
    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(dest_path)],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            return f"Failed to run GitHub Updater: Git clone failed: {r.stderr.strip()}"
    except Exception as e:
        return f"Failed to run GitHub Updater: Git execution error: {e}"

    print("[GitHub Updater] Repository cloned. Analyzing structure...")
    
    # 2. Gather file lists
    all_files = []
    py_files = []
    doc_files = []
    
    for root, dirs, files in os.walk(dest_path):
        # Skip git files
        if ".git" in root:
            continue
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), dest_path)
            all_files.append(rel)
            if f.endswith(".py"):
                py_files.append(rel)
            elif f.lower() in ("readme.md", "readme", "install.md", "setup.py", "requirements.txt"):
                doc_files.append(rel)

    print(f"[GitHub Updater] Found {len(all_files)} files, {len(py_files)} python files, {len(doc_files)} docs.")

    # 3. Read important documents
    doc_contents = []
    readme_path = dest_path / "README.md"
    if not readme_path.exists():
        # Fallback to other casing
        for f in doc_files:
            if "readme" in f.lower():
                readme_path = dest_path / f
                break

    if readme_path.exists():
        try:
            readme_text = readme_path.read_text(encoding="utf-8", errors="ignore")
            doc_contents.append(f"--- README.md ---\n{readme_text[:3000]}") # Cap at 3k chars
        except:
            pass

    # Read requirements or setup if present
    req_path = dest_path / "requirements.txt"
    if req_path.exists():
        try:
            req_text = req_path.read_text(encoding="utf-8", errors="ignore")
            doc_contents.append(f"--- requirements.txt ---\n{req_text[:1000]}")
        except:
            pass

    # Read up to 2 python file headers to see code patterns
    py_contents = []
    for f in py_files[:2]:
        p = dest_path / f
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
            py_contents.append(f"--- File: {f} ---\n{t[:1500]}")
        except:
            pass

    docs_payload = "\n\n".join(doc_contents)
    code_payload = "\n\n".join(py_contents)

    # 4. Analyze using Gemini
    config_path = BASE_DIR / "config" / "api_keys.json"
    if not config_path.exists():
        return "Failed to run GitHub Updater: API keys configuration not found."

    try:
        api_keys = json.loads(config_path.read_text(encoding="utf-8"))
        gemini_key = api_keys.get("gemini_api_key")
        if not gemini_key:
            return "Failed to run GitHub Updater: gemini_api_key is empty."
    except Exception as e:
        return f"Failed to run GitHub Updater: Error reading API keys: {e}"

    print("[GitHub Updater] Invoking Gemini code analyst...")
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        
        prompt = f"""
Analyze this GitHub Repository structure and content.
We want to extract useful tools, actions, dependencies, or architectures that we can integrate to improve ourselves.

Repository: {repo_owner}/{repo_name}
All Files List:
{json.dumps(all_files[:60], indent=2)}

Documentation & Configuration:
{docs_payload}

Sample Code Headers:
{code_payload}

Generate a concise markdown study report. It should contain:
1. **Overview & Features**: What does this repository do?
2. **Key APIs/Dependencies**: What libraries are used?
3. **Integration Recommendations**: Provide EXACT recommendations on how J.A.R.V.I.S. can write a python action file inside `C:\\Users\\HP\\jarvis\\actions\\` or run commands to integrate this functionality. Include code patterns if applicable.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        report = response.text or "Error: Empty analysis response."
        
        # Write report to C:\Users\HP\jarvis\scratch\github_studies\<repo_name>_report.md
        report_path = STUDIES_DIR / f"{repo_name}_report.md"
        report_path.write_text(report, encoding="utf-8")
        
        print(f"[GitHub Updater] Study report created at: {report_path}")
        
        # Also copy it as a markdown artifact for user view
        artifact_dir = Path("C:/Users/HP/.gemini/antigravity/brain/d4843218-84b8-421a-ab9e-2517e70e2dd2")
        if artifact_dir.exists():
            art_path = artifact_dir / f"repo_study_{repo_name}.md"
            art_path.write_text(report, encoding="utf-8")
            print(f"[GitHub Updater] Artifact saved to: {art_path}")

        return f"Successfully studied repository {repo_name}!\nDetailed report generated at: {report_path.name}\nWe can now write custom python actions to automate these features."

    except Exception as e:
        return f"Failed to run GitHub Updater: Analysis error: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(run_github_updater(sys.argv[1]))
    else:
        print("Please provide a repository URL.")
