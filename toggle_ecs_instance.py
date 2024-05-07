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


@click.command()
@click.option("--cluster", help="Cluster short name", required=True)
@click.option("--service", help="ECS Tasks family name", required=True)
@click.option("--turn-on/--turn-off", help="ON or OFF", required=False)
def toggle_service(cluster, service, turn_on):
    client = boto3.client("ecs")

    try:
        if (turn_on):
            update_ecs_instance_app_count(client, cluster, service, 1)
        else:
            update_ecs_instance_app_count(client, cluster, service, 0)

        print("Service toggled!")
    except Exception as e:
        print(f"Error: An error ocurred while toggling the service: {e}")


if __name__ == "__main__":
    toggle_service()
