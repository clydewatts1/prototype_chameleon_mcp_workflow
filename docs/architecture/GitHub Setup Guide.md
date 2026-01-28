# **Exporting and Uploading to GitHub**

Follow these steps to move your Constitutional Architecture documents from this environment to a GitHub repository.

## **1\. Local Environment Preparation**

Open your terminal (or Command Prompt) and create a directory structure that matches the file paths we defined:

\# Create the project folders  
mkdir \-p chameleon-docs/docs/architecture  
cd chameleon-docs

## **2\. Exporting the Files**

Since this environment is collaborative, you will need to manually save the files. For each file we generated (e.g., Role\_Behavior\_Specs.md, Guard\_Behavior\_Specs.md):

1. Click the **Copy** or **Download** icon in the top right of the file's tab in the editor.  
2. Create a new file in your local docs/architecture/ folder with the same name.  
3. Paste the content and save.

## **3\. Initializing Git**

In your project root (chameleon-docs/), run the following commands:

\# Initialize the repository  
git init

\# Add all files  
git add .

\# Create your first commit  
git commit \-m "Initial commit: Constitutional Architecture Stack"

## **4\. Connecting to GitHub**

1. Go to [GitHub](https://github.com) and create a new repository named chameleon-docs. Do **not** initialize it with a README or License yet.  
2. Copy the remote repository URL (e.g., https://github.com/your-username/chameleon-docs.git).  
3. Back in your terminal:

\# Add the remote origin  
git remote add origin \[https://github.com/your-username/chameleon-docs.git\](https://github.com/your-username/chameleon-docs.git)

\# Set your branch to main  
git branch \-M main

\# Push the files  
git push \-u origin main

## **5\. Verifying the Stack**

Once pushed, your GitHub repository will reflect the full directory structure we built:

* docs/architecture/ (containing Specs, DB Schema, Lifecycle, etc.)  
* docs/roadmap.md  
* docs/Branching\_Logic\_Guide.md