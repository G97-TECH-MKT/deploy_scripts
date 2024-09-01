import boto3
import sys
import os
import json


def get_parameters(param_names):
    """Fetch parameters from AWS SSM in chunks of 10 (API limit)."""
    ssm = boto3.client('ssm')
    parameters = []
    for i in range(0, len(param_names), 10):
        chunk = param_names[i:i + 10]
        response = ssm.get_parameters(Names=chunk, WithDecryption=True)
        parameters.extend(response['Parameters'])
    return {param['Name']: param['Value'] for param in parameters}


def parse_parameter_input(input_param):
    """Parse input parameters expected in 'key:value' format."""
    parts = input_param.split(":")
    if len(parts) != 2:
        raise ValueError("El parámetro debe tener el formato 'tipo_variable:nombre_parametro'")
    return parts[0], parts[1]


def parse_value(value):
    """Try to parse the value as JSON, otherwise return it as-is."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python get_parameters.py <tipo_variable1>:<nombre-parametro1> <tipo_variable2>:<nombre_parametro2> etc")
        sys.exit(1)

    input_params = sys.argv[1:]
    try:
        env_vars = {}
        param_names = []
        for input_param in input_params:
            env_var, param_name = parse_parameter_input(input_param)
            env_vars[param_name] = env_var
            param_names.append(param_name)

        params = get_parameters(param_names)

        github_env_path = os.getenv('GITHUB_ENV')
        if github_env_path:
            with open(github_env_path, 'a') as f:
                for param_name, param_value in params.items():
                    env_var = env_vars.get(param_name, param_name)
                    parsed_value = parse_value(param_value)
                    if isinstance(parsed_value, str):
                        parsed_value = parsed_value.replace('"', '\\"')
                    f.write(f"{env_var.upper()}={parsed_value}\n")
        else:
            print("La variable de entorno GITHUB_ENV no está definida.")
            sys.exit(1)
    except Exception as e:
        print(f"Error al obtener los parámetros: {e}")
        sys.exit(1)
