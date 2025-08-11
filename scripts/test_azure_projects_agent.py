#!/usr/bin/env python3
import os
import argparse
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder


def main():
    parser = argparse.ArgumentParser(description="Test Azure AI Projects Agent call")
    parser.add_argument("message", nargs="?", default="Hi Agent628", help="Message to send to the agent")
    parser.add_argument("--endpoint", default=os.getenv("AZURE_AI_PROJECTS_ENDPOINT", "https://momah-open-ai-project-resource.services.ai.azure.com/api/projects/momah-open-ai-project"), help="Azure AI Projects endpoint")
    parser.add_argument("--agent-id", default=os.getenv("AZURE_AI_PROJECTS_AGENT_ID", "asst_Yr3GKYuAIBoma6rod05Xfs6l"), help="Agent ID")
    args = parser.parse_args()

    print(f"Using endpoint: {args.endpoint}")
    print(f"Using agent id: {args.agent_id}")

    try:
        project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=args.endpoint,
        )
        agent = project.agents.get_agent(args.agent_id)
        thread = project.agents.threads.create()
        print(f"Created thread, ID: {thread.id}")

        project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=args.message,
        )

        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
        )

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            sys.exit(2)

        messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        printed = False
        for m in messages:
            if m.text_messages:
                last = m.text_messages[-1].text.value
                print(f"{m.role}: {last}")
                printed = True
        if not printed:
            print("No text messages returned.")
            sys.exit(3)
        sys.exit(0)

    except Exception as e:
        print("Error calling Azure AI Projects agent:", e)
        print("Hint: ensure DefaultAzureCredential can authenticate. For local dev, set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET or login via Azure CLI.")
        sys.exit(1)


if __name__ == "__main__":
    main() 