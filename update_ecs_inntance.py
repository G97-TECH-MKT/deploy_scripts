import boto3
import click
import json

def get_current_task_definition(client, cluster, service):
    """Retrieve the current ECS task definition for a given service."""
    response = client.describe_services(cluster=cluster, services=[service])
    current_task_arn = response["services"][0]["taskDefinition"]
    print("Current task ARN:", current_task_arn)
    return client.describe_task_definition(taskDefinition=current_task_arn)

@click.command()
@click.option("--cluster", help="Name of the ECS cluster", required=True)
@click.option("--service", help="Name of the ECS service", required=True)
@click.option("--image", help="Docker image URL for the updated application", required=True)
@click.option("--username-secret-arn", help="ARN for the username secret in AWS Secrets Manager", required=True)
@click.option("--password-secret-arn", help="ARN for the password secret in AWS Secrets Manager", required=True)
@click.option("--env-vars-file", help="File path of environment variables in JSON format", required=True)
def deploy(cluster, service, image, username_secret_arn, password_secret_arn, env_vars_file):
    """Deploy an updated application to an ECS service."""
    client = boto3.client("ecs")

    # Read environment variables from the JSON file
    with open(env_vars_file, 'r') as file:
        new_env_vars = json.load(file)

    # Fetch the current task definition
    print("Fetching current task definition...")
    response = get_current_task_definition(client, cluster, service)
    container_definition = response["taskDefinition"]["containerDefinitions"][0].copy()

    # Update the container definition with the new image
    container_definition["image"] = image

    # Update the environment and secrets in the container definition
    container_definition["environment"] = new_env_vars
    container_definition["secrets"] = [
        {"name": "DB_USERNAME", "valueFrom": username_secret_arn},
        {"name": "DB_PASSWORD", "valueFrom": password_secret_arn}
    ]

    print(f"Updated image to: {image}")

    # Register a new task definition
    print("Registering new task definition...")
    new_task_definition = client.register_task_definition(
        family=response["taskDefinition"]["family"],
        volumes=response["taskDefinition"]["volumes"],
        containerDefinitions=[container_definition],
        cpu=response["taskDefinition"]["cpu"],
        memory=response["taskDefinition"]["memory"],
        networkMode=response["taskDefinition"]["networkMode"],
        requiresCompatibilities=response["taskDefinition"]["requiresCompatibilities"],
        executionRoleArn=response["taskDefinition"]["executionRoleArn"],
        taskRoleArn=response["taskDefinition"]["taskRoleArn"],
    )
    new_task_arn = new_task_definition["taskDefinition"]["taskDefinitionArn"]
    print(f"New task definition ARN: {new_task_arn}")

    # Update the service with the new task definition
    print("Updating ECS service with new task definition...")
    client.update_service(
        cluster=cluster,
        service=service,
        taskDefinition=new_task_arn,
    )
    print("Service updated successfully!")

if __name__ == "__main__":
    deploy()
