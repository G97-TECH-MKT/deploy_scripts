import boto3
import subprocess
import sys
import psycopg2
import time

def get_secret_value(secret_arn):
    """get secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return response['SecretString']  # Return value in pure string


def create_ssh_tunnel(ssh_key, bastion_user, bastion_host, local_port, remote_host, remote_port):
    """Establishes an SSH tunnel for the port forwarding connection."""
    ssh_command = [
        "ssh", "-i", ssh_key, "-N", "-L",
        f"{local_port}:{remote_host}:{remote_port}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{bastion_user}@{bastion_host}"
    ]
    return subprocess.Popen(ssh_command)


def create_database(host, port, username, password, db_name):
    """Try to crear a database if nor exists"""
    try:
        conn = psycopg2.connect(host=host, port=port, user=username, password=password, dbname='postgres')

        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
            if cur.fetchone() is not None:
                print(f"La base de datos '{db_name}' ya existe.")
            else:
                cur.execute(f"CREATE DATABASE {db_name};")
                print(f"Base de datos '{db_name}' creada con éxito.")
    except Exception as e:
        print(f"Error al crear la base de datos '{db_name}': {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    bastion_host = sys.argv[1]
    bastion_user = sys.argv[2]
    local_port = sys.argv[3]  # local port for  SSH tunnel
    remote_host = sys.argv[4]  # RDS Endpoint
    remote_port = sys.argv[5]  # RDS Port
    db_name = sys.argv[6]
    ssh_key_secret_arn = sys.argv[7]
    db_username_secret_arn = sys.argv[8]
    db_password_secret_arn = sys.argv[9]

    # Recover secrets value
    ssh_key_secret = get_secret_value(ssh_key_secret_arn)
    db_username_secret = get_secret_value(db_username_secret_arn)
    db_password_secret = get_secret_value(db_password_secret_arn)

    # Write SSH key in a temp file
    ssh_key_path = "/tmp/key.pem"
    with open(ssh_key_path, "w") as file:
        file.write(ssh_key_secret)  # Write string directly to file
    subprocess.run(["chmod", "600", ssh_key_path])

    # Create SSH tunnel
    tunnel = create_ssh_tunnel(ssh_key_path, bastion_user, bastion_host, local_port, remote_host, remote_port)

    time.sleep(5) # This time is mandatory to wait for the SSH tunnel to be established


    try:
        # Create database through SSH Tunel
        create_database('localhost', local_port, db_username_secret, db_password_secret, db_name)
    finally:
        # Close SSH Tunel and clean
        tunnel.terminate()
        subprocess.run(["rm", ssh_key_path])
