"""Enable the verified fresh deployment at boot after explicit guided consent."""
from .accounts import provisioning_gate
from .execution import Execution


def enable_startup(config, name, state_directory):
    from .reference import existing_service
    from .lifecycle import command, service_status
    provisioning_gate()
    with Execution(state_directory, {'operation': 'reference-apply-v1', 'config': config, 'name': name}) as state:
        if state.state.get('phase') != 'reference_poc_ready':
            raise ValueError('Finish installation before enabling automatic startup')
        unit = existing_service(config, name, state)
        if unit != 'installarr-' + name + '.service' or service_status(name).get('phase') != 'containers_running':
            raise ValueError('The verified deployment must be running before enabling automatic startup')
        units = ['docker.service', 'containerd.service', unit]
        command(['systemctl', 'enable'] + units)
        if command(['systemctl', 'is-enabled'] + units).splitlines() != ['enabled'] * len(units):
            raise ValueError('Automatic startup verification failed; run setup again to continue')
        state.state['automatic_startup'] = 'verified'
        state._save()
    return {'automatic_startup': 'enabled', 'units': units}
