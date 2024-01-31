import boto3
import click
import json

def get_current_task_definition(client, cluster, service):
    response = client.describe_services(cluster=cluster, services=[service])
    current_task_arn = response["services"][0]["taskDefinition"]

    print("≠ current_task_arn ≠")
    print(current_task_arn)
    return client.describe_task_definition(taskDefinition=current_task_arn)

@click.command()
@click.option("--cluster", help="Name of the ECS cluster", required=True)
@click.option("--service", help="Name of the ECS service", required=True)
@click.option("--image", help="Docker image URL for the updated application", required=True)
@click.option("--username-secret-arn", help="Username ARN for the database credentials secret", required=True)
@click.option("--password-secret-arn", help="Password ARN for the database credentials secret", required=True)
@click.option("--env-vars", help="JSON string of environment variables", required=True)
def deploy(cluster, service, image, username_secret_arn, password_secret_arn, env_vars):
    client = boto3.client("ecs")

    # Fetch the current task definition
    print("Fetching current task definition...")
    response = get_current_task_definition(client, cluster, service)
    container_definition = response["taskDefinition"]["containerDefinitions"][0].copy()

    # Update the container definition with the new image
    container_definition["image"] = image

    # Update the container definition with new environment variables
    new_env_vars = json.loads(env_vars)
    container_definition["environment"] = new_env_vars
    container_definition["secrets"] = [
        {"name": "DB_USERNAME", "valueFrom": username_secret_arn},
        {"name": "DB_PASSWORD", "valueFrom": password_secret_arn}
    ]

    print(f"Updated image to: {image}")

    # Register a new task definition
    print("Registering new task definition...")

    response = client.register_task_definition(
        family=response["taskDefinition"]["family"],
        volumes=response["taskDefinition"]["volumes"],
        containerDefinitions=[container_definition],
        cpu="256",  # Modify based on your needs
        memory="512",  # Modify based on your needs
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        executionRoleArn="dev_ecs_task_execution_role",
        taskRoleArn="dev_ecs_task_execution_role",
    )
    new_task_arn = response["taskDefinition"]["taskDefinitionArn"]
    print(f"New task definition ARN: {new_task_arn}")

    # Update the service with the new task definition
    print("Updating ECS service with new task definition...")
    client.update_service(
        cluster=cluster, service=service, taskDefinition=new_task_arn,
    )
    print("Service updated!")

if __name__ == "__main__":
    deploy()
