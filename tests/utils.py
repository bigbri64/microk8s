import datetime
import time
import yaml
import platform
from subprocess import check_output, CalledProcessError


arch_translate = {
    'aarch64': 'arm64',
    'x86_64': 'amd64'
}

def run_until_success(cmd, timeout_insec=60):
    """
    Run a command untill it succeeds or times out.
    Args:
        cmd: Command to run
        timeout_insec: Time out in seconds

    Returns: The string output of the command

    """
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
    while True:
        try:
            output = check_output(cmd.split()).strip().decode('utf8')
            return output.replace('\\n', '\n')
        except CalledProcessError:
            if datetime.datetime.now() > deadline:
                raise
            print("Retrying {}".format(cmd))
            time.sleep(3)


def kubectl(cmd, timeout_insec=300):
    """
    Do a kubectl <cmd>
    Args:
        cmd: left part of kubectl <left_part> command
        timeout_insec: timeout for this job

    Returns: the kubectl response in a string

    """
    cmd = '/snap/bin/microk8s.kubectl ' + cmd
    return run_until_success(cmd, timeout_insec)


def docker(cmd):
    """
    Do a docker <cmd>
    Args:
        cmd: left part of docker <left_part> command

    Returns: the docker response in a string

    """
    cmd = '/snap/bin/microk8s.docker ' + cmd
    return run_until_success(cmd)


def kubectl_get(target, timeout_insec=300):
    """
    Do a kubectl get and return the results in a yaml structure.
    Args:
        target: which resource we are getting
        timeout_insec: timeout for this job

    Returns: YAML structured response

    """
    cmd = 'get -o yaml ' + target
    output = kubectl(cmd, timeout_insec)
    return yaml.load(output)


def wait_for_pod_state(pod, namespace, desired_state, desired_reason=None, label=None):
    """
    Wait for a a pod state. If you do not specify a pod name and you set instead a label
    only the first pod will be checked.
    """
    while True:
        cmd = 'po {} -n {}'.format(pod, namespace)
        if label:
            cmd += ' -l {}'.format(label)
        data = kubectl_get(cmd, 300)
        if pod == "":
            if len(data['items']) > 0:
                status = data['items'][0]['status']
            else:
                status = []
        else:
            status = data['status']
        if 'containerStatuses' in status:
            container_status = status['containerStatuses'][0]
            state, details = list(container_status['state'].items())[0]
            if desired_reason:
                reason = details.get('reason')
                if state == desired_state and reason == desired_reason:
                    break
            elif state == desired_state:
                break
        time.sleep(3)


def wait_for_installation():
    """
    Wait for kubernetes service to appear.
    """
    while True:
        cmd = 'svc kubernetes'
        data = kubectl_get(cmd, 300)
        service = data['metadata']['name']
        if 'kubernetes' in service:
            break
        else:
            time.sleep(3)

    while True:
        cmd = 'get no'
        nodes = kubectl(cmd, 300)
        if ' Ready' in nodes:
            break
        else:
            time.sleep(3)

    # Allow rest of the services to come up
    time.sleep(30)


def microk8s_enable(addon):
    """
    Disable an addon

    Args:
        addon: name of the addon

    """
    cmd = '/snap/bin/microk8s.enable {}'.format(addon)
    return run_until_success(cmd, timeout_insec=300)


def microk8s_disable(addon):
    """
    Enable an addon

    Args:
        addon: name of the addon

    """
    cmd = '/snap/bin/microk8s.disable {}'.format(addon)
    return run_until_success(cmd, timeout_insec=300)


def microk8s_reset():
    """
    Call microk8s reset
    """
    cmd = '/snap/bin/microk8s.reset'
    run_until_success(cmd, timeout_insec=300)
    wait_for_installation()


def update_yaml_with_arch(manifest_file):
    """
    Updates any $ARCH entry with the architecture in the manifest

    """
    arch = arch_translate[platform.machine()]
    with open(manifest_file) as f:
        s = f.read()

    with open(manifest_file, 'w') as f:
        s = s.replace('$ARCH', arch)
        f.write(s)
