import boto3
import click


def update_ecs_instance_app_count(client, cluster, service, app_count):
    client.update_service(
        cluster=cluster,
        service=service,
        desiredCount=app_count,
    )
    print(
        f"Service {service} app count {'increased' if app_count == 1 else 'decreased'}!")


def toggle_single_service(client, cluster, service, turn_on):
    if (turn_on):
        update_ecs_instance_app_count(client, cluster, service, 1)
    else:
        update_ecs_instance_app_count(client, cluster, service, 0)


@click.command()
@click.option("--cluster", help="Cluster short name", required=True)
@click.option("--turn-on/--turn-off", help="ON or OFF", required=True)
@click.option("--service", help="ECS Tasks family name", required=False)
@click.option("--shutdown-all-cluster-tasks", help="Indicates the shutdown of all the cluster tasks", required=False, is_flag=True)
def toggle_service(cluster, service, turn_on, shutdown_all_cluster_tasks):
    client = boto3.client("ecs")

    try:
        if (shutdown_all_cluster_tasks):
            response = client.list_services(cluster=cluster)
            for service in response["serviceArns"]:
                toggle_single_service(client, cluster, service, turn_on)
            print("All services were toggled!")
            return
        else:
            toggle_single_service(client, cluster, service, turn_on)

    except Exception as e:
        print(f"Error: An error ocurred while toggling the services: {e}")


if __name__ == "__main__":
    toggle_service()
