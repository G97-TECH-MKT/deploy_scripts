import boto3
import click
import json


def get_current_task_definition(client, cluster, service):
    response = client.describe_services(cluster=cluster, services=[service])
    current_task_arn = response["services"][0]["taskDefinition"]

    print("≠ current_task_arn ≠")
    print(current_task_arn)
    return client.describe_task_definition(taskDefinition=current_task_arn)


PROD_TASK_ROLE = "production_ecs_task_execution_role"
DEV_TASK_ROLE = "dev_ecs_task_execution_role"


@click.command()
@click.option("--cluster", help="Name of the ECS cluster", required=True)
@click.option("--service", help="Name of the ECS service", required=True)
@click.option("--image", help="Docker image URL for the updated application", required=True)
@click.option("--username-secret-arn", help="Username ARN for the database credentials secret", required=True)
@click.option("--password-secret-arn", help="Password ARN for the database credentials secret", required=True)
@click.option("--target-env", help="Target environment (production or dev)", required=False)
@click.option("--env-vars", help="JSON string of environment variables", required=True)
@click.option("--container-names", help="Comma-separated list of container names to update (optional, updates all if not provided)", required=False)
@click.option("--additional-secrets", help="JSON string of additional secrets in format {\"SECRET_NAME\": \"arn:aws:secretsmanager:...\"}", required=False)
def deploy(cluster, service, image, username_secret_arn, password_secret_arn, target_env, env_vars, container_names, additional_secrets):
    client = boto3.client("ecs")

    # Fetch the current task definition
    print("Fetching current task definition...")
    response = get_current_task_definition(client, cluster, service)
    task_def = response["taskDefinition"]

    # Parse container names if provided
    containers_to_update = []
    if container_names:
        containers_to_update = [name.strip() for name in container_names.split(",")]
        print(f"Containers to update: {containers_to_update}")
    else:
        print("No specific containers specified, will update all containers")

    updated_container_definitions = []
    new_env_vars = json.loads(env_vars)

    for container_def in task_def["containerDefinitions"]:
        container_name = container_def.get("name", "")
        updated_container = container_def.copy()

        should_update = not containers_to_update or container_name in containers_to_update

        if should_update:
            updated_container["image"] = image
            print(f"Updating container '{container_name}' with image: {image}")

            existing_env = {item["name"]: item["value"] for item in updated_container.get("environment", [])}
            new_env_dict = {item["name"]: item["value"] for item in new_env_vars}
            existing_env.update(new_env_dict)
            updated_container["environment"] = [{"name": k, "value": v} for k, v in existing_env.items()]

            existing_secrets = {}
            for secret in updated_container.get("secrets", []):
                secret_name = secret.get("name")
                secret_value = secret.get("valueFrom") or secret.get("value")
                existing_secrets[secret_name] = secret_value

            existing_secrets["DB_USERNAME"] = username_secret_arn
            existing_secrets["DB_PASSWORD"] = password_secret_arn

            # Add additional secrets if provided
            if additional_secrets:
                additional_secrets_dict = json.loads(additional_secrets)
                existing_secrets.update(additional_secrets_dict)
                print(f"Added {len(additional_secrets_dict)} additional secret(s)")

            updated_container["secrets"] = [
                {"name": k, "valueFrom": v} for k, v in existing_secrets.items()
            ]
        else:
            print(f"Keeping container '{container_name}' unchanged (not in update list)")

        updated_container_definitions.append(updated_container)

    print(f"Total containers in task definition: {len(updated_container_definitions)}")
    for container in updated_container_definitions:
        print(f"  - {container.get('name')}: {container.get('image')}")

    print("Registering new task definition...")

    task_execution_role = PROD_TASK_ROLE if target_env == "production" else DEV_TASK_ROLE

    register_params = {
        "family": task_def["family"],
        "containerDefinitions": updated_container_definitions,
        "requiresCompatibilities": task_def.get("requiresCompatibilities", ["FARGATE"]),
        "executionRoleArn": task_execution_role,
        "taskRoleArn": task_execution_role,
    }

    if "volumes" in task_def:
        register_params["volumes"] = task_def["volumes"]
    if "cpu" in task_def:
        register_params["cpu"] = task_def["cpu"]
    if "memory" in task_def:
        register_params["memory"] = task_def["memory"]
    if "networkMode" in task_def:
        register_params["networkMode"] = task_def["networkMode"]
    else:
        register_params["networkMode"] = "awsvpc"
    if "runtimePlatform" in task_def:
        register_params["runtimePlatform"] = task_def["runtimePlatform"]
    if "placementConstraints" in task_def:
        register_params["placementConstraints"] = task_def["placementConstraints"]
    if "ipcMode" in task_def:
        register_params["ipcMode"] = task_def["ipcMode"]
    if "pidMode" in task_def:
        register_params["pidMode"] = task_def["pidMode"]
    if "proxyConfiguration" in task_def:
        register_params["proxyConfiguration"] = task_def["proxyConfiguration"]
    if "ephemeralStorage" in task_def:
        register_params["ephemeralStorage"] = task_def["ephemeralStorage"]

    response = client.register_task_definition(**register_params)
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
