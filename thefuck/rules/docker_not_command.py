from itertools import dropwhile, takewhile, islice
import re
import subprocess
from thefuck.utils import replace_command, for_app, which, cache, get_close_matches_with_hyphen
from thefuck.specific.sudo import sudo_support
from difflib import get_close_matches


@sudo_support
@for_app('docker')
def match(command):
    return 'is not a docker command' in command.output or 'Usage:	docker' in command.output


def _parse_commands(lines, starts_with):
    lines = dropwhile(lambda line: not line.startswith(starts_with), lines)
    lines = islice(lines, 1, None)
    lines = list(takewhile(lambda line: line.strip(), lines))
    return [line.strip().split(' ')[0] for line in lines]


def get_docker_commands():
    proc = subprocess.Popen('docker', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Old version docker returns its output to stdout, while newer version returns to stderr.
    lines = proc.stdout.readlines() or proc.stderr.readlines()
    lines = [line.decode('utf-8') for line in lines]

    # Only newer versions of docker have management commands in the help text.
    if 'Management Commands:\n' in lines:
        management_commands = _parse_commands(lines, 'Management Commands:')
    else:
        management_commands = []
    regular_commands = _parse_commands(lines, 'Commands:')

    docker_compose_commands = get_docker_compose_subcommands()
    print(f"docker_compose_commands: {docker_compose_commands}")
    return management_commands + regular_commands + docker_compose_commands


def get_docker_compose_subcommands():
    try:
        # Note: 'docker compose --help' provides a list of subcommands
        command_name =["docker", "compose", "--help"]
        proc = subprocess.Popen(command_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Old version docker returns its output to stdout, while newer version returns to stderr.
        lines = proc.stdout.readlines() or proc.stderr.readlines()
        lines = [line.decode('utf-8') for line in lines]

        # Parse and return commands
        return _parse_commands(lines, 'Commands:')
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    # Decode the output
    stdout_lines = stdout.decode('utf-8').splitlines()
    stderr_lines = stderr.decode('utf-8').splitlines()

    # Debugging: Print the raw output
    print("STDOUT LINES:")
    for line in stdout_lines:
        print(line)
    print("STDERR LINES:")
    for line in stderr_lines:
        print(line)

    # Old version docker-compose returns its output to stdout, while newer version returns to stderr.
    lines = proc.stdout.readlines() or proc.stderr.readlines()
    lines = [line.decode('utf-8') for line in lines]

    return _parse_commands(lines, 'Commands:')


if which('docker'):
    get_docker_commands = cache(which('docker'))(get_docker_commands)


@sudo_support
def get_new_command(command):
    if 'Usage:' in command.output and len(command.script_parts) > 1:
        management_subcommands = _parse_commands(command.output.split('\n'), 'Commands:')
        return replace_command(command, command.script_parts[2], management_subcommands)

    cmd_match = re.findall(r"docker: '(\w+)' is not a docker command.", command.output)
    if cmd_match:
        wrong_command = cmd_match[0]
        return replace_command(command, wrong_command, get_docker_commands())
    else:
        # check if the command is close to a docker command
        matched = get_close_matches_with_hyphen(command.script_parts[1], get_docker_commands(), cutoff=0.6)
        if matched:
            return replace_command(command, command.script_parts[0], matched)
        else:
            return None
