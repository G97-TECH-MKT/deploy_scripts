import boto3
import sys
import os

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python script.py <tipo_variable1>:<nombre-parametro1> <tipo_variable2>:<nombre-parametro2> etc")
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

        # Escribir en el archivo de entorno de GitHub Actions
        with open(os.getenv('GITHUB_ENV'), 'a') as f:
            for param_name, param_value in params.items():
                env_var = env_vars[param_name]
                f.write(f"{env_var.upper()}={param_value}\n")
    except Exception as e:
        print(f"Error al obtener los parámetros: {e}")
        sys.exit(1)
