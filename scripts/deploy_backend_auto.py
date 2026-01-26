#!/usr/bin/env python3
"""
Automatic backend deployment script.
Uses Railway and Vercel APIs to deploy backend and connect to frontend.
"""
import os
import json
import requests
import time
import sys

# Configuration
RAILWAY_TOKEN = os.getenv('RAILWAY_ACCESS_TOKEN', '7c5eba67-37b9-46df-8537-3455bf65ff0f')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN', '')
RAILWAY_API = "https://backboard.railway.app/graphql/v2"
VERCEL_API = "https://api.vercel.com"

def railway_graphql(query, variables=None):
    """Execute Railway GraphQL query."""
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(RAILWAY_API, json=payload, headers=headers)
    return response.json()

def create_railway_project():
    """Create a new Railway project."""
    print("Creating Railway project...")

    query = """
    mutation ProjectCreate($input: ProjectCreateInput!) {
      projectCreate(input: $input) {
        id
        name
      }
    }
    """

    variables = {
        "input": {
            "name": "radtest-backend",
            "description": "RADTest Backend API - Auto deployed"
        }
    }

    result = railway_graphql(query, variables)

    if 'errors' in result:
        print(f"Error creating project: {result['errors']}")
        return None

    project_id = result['data']['projectCreate']['id']
    print(f"✓ Project created: {project_id}")
    return project_id

def deploy_from_github(project_id):
    """Deploy backend from GitHub to Railway."""
    print("Setting up GitHub deployment...")

    # Note: This requires GitHub integration to be set up
    # For now, we'll create a service that can be manually connected

    query = """
    mutation ServiceCreate($input: ServiceCreateInput!) {
      serviceCreate(input: $input) {
        id
      }
    }
    """

    variables = {
        "input": {
            "projectId": project_id,
            "name": "backend",
            "source": {
                "repo": "InterceptArcher/RADTest",
                "branch": "main",
                "rootDirectory": "backend"
            }
        }
    }

    result = railway_graphql(query, variables)

    if 'errors' in result:
        print(f"Note: {result.get('errors', 'Could not auto-deploy from GitHub')}")
        print("You'll need to connect GitHub manually in Railway dashboard")
        return None

    service_id = result['data']['serviceCreate']['id']
    print(f"✓ Service created: {service_id}")
    return service_id

def get_vercel_projects():
    """Get list of Vercel projects."""
    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
    }

    response = requests.get(f"{VERCEL_API}/v9/projects", headers=headers)

    if response.status_code != 200:
        print(f"Error getting Vercel projects: {response.status_code}")
        return []

    return response.json().get('projects', [])

def update_vercel_env(project_id, backend_url):
    """Update Vercel environment variable."""
    print(f"Updating Vercel frontend with backend URL...")

    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "Content-Type": "application/json"
    }

    # Create or update environment variable
    payload = {
        "key": "NEXT_PUBLIC_API_URL",
        "value": backend_url,
        "type": "encrypted",
        "target": ["production", "preview", "development"]
    }

    response = requests.post(
        f"{VERCEL_API}/v10/projects/{project_id}/env",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        print(f"✓ Environment variable updated")
        return True
    else:
        print(f"Error updating env var: {response.status_code} - {response.text}")
        return False

def trigger_vercel_redeploy(project_name):
    """Trigger Vercel redeployment."""
    print("Triggering frontend redeployment...")

    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
    }

    # Get latest deployment
    response = requests.get(
        f"{VERCEL_API}/v6/deployments?projectId={project_name}&limit=1",
        headers=headers
    )

    if response.status_code == 200:
        deployments = response.json().get('deployments', [])
        if deployments:
            print("✓ Latest deployment found - redeploy via dashboard or CLI")
            return True

    return False

def main():
    print("=" * 60)
    print("Automatic Backend Deployment")
    print("=" * 60)
    print()

    # Step 1: Create Railway project
    project_id = create_railway_project()

    if not project_id:
        print("\n⚠️  Could not create Railway project automatically")
        print("\nManual deployment required:")
        print("1. Go to: https://railway.app/new")
        print("2. Deploy from GitHub: InterceptArcher/RADTest")
        print("3. Select directory: backend")
        sys.exit(1)

    print()
    print("=" * 60)
    print("✓ Railway Project Created Successfully!")
    print("=" * 60)
    print()
    print(f"Project ID: {project_id}")
    print(f"View at: https://railway.app/project/{project_id}")
    print()
    print("NEXT STEPS:")
    print("-" * 60)
    print("1. Open Railway dashboard: https://railway.app/dashboard")
    print("2. Find your 'radtest-backend' project")
    print("3. Click 'New' → 'GitHub Repo'")
    print("4. Select: InterceptArcher/RADTest")
    print("5. Set root directory: backend")
    print("6. Deploy!")
    print()
    print("7. Once deployed, go to Settings → Generate Domain")
    print("8. Copy your backend URL")
    print("9. Run this command with your backend URL:")
    print()
    print("   ./scripts/update_frontend_url.py <backend-url>")
    print()
    print("=" * 60)

    # Try to get Vercel projects if token available
    if VERCEL_TOKEN:
        print("\nChecking Vercel projects...")
        projects = get_vercel_projects()

        if projects:
            print(f"Found {len(projects)} Vercel project(s)")
            for proj in projects:
                if 'frontend' in proj['name'].lower():
                    print(f"  - {proj['name']} (ID: {proj['id']})")
        else:
            print("Note: Could not access Vercel projects")

if __name__ == "__main__":
    main()
