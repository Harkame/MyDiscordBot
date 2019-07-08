from yaml import Loader, load, dump

def get_config(config_file_path):
    config_stream = open(config_file_path, 'r')

    config_file = load(config_stream, Loader=Loader)

    config_stream.close()

    return config_file;

def write_config(config_file_path, data):
    with open(config_file_path, 'w') as yaml_file:
        dump(data, yaml_file, default_flow_style=False)
