from pydantic import validate_arguments, Dict, Any

from aga_swarm.swarm.types import SwarmID, ActionSpaceMetadata
from aga_swarm.swarm.swarm_utils import get_action_space_metadata

def action(action_id: str, params: Dict[str, Any], swarm_id: SwarmID) -> dict:
    """
        Passes the action to the appropriate action_type for execution.

        This function serves as a universal entry point for executing actions.

        Every action action_type is expected to follow the default_swarm_action.py
        action type.
    """
    action_space_metadata: ActionSpaceMetadata = get_action_space_metadata(swarm_id)
    
    # Get config parameters required for this action
    required_configs = action_space_metadata[action_id].required_configs
    for config in required_configs: 
        try:
            if getattr(swarm_id.configs, config) is None:
                raise KeyError
            params[config] = getattr(swarm_id.configs, config)
        except KeyError:
            raise KeyError(f"Config {config} not found in swarm configs or value is None")
    
    # Import the main function from the path specified by the action_id
    action_type = action_type.replace('/', '.')
    if action_type.endswith('.py'):
        action_type = action_type[:-3]
    action = __import__(action_type, fromlist=[''])
    if hasattr(action, 'main'):
        main_function = getattr(action, 'main')
    else:
        raise AttributeError("No main function found in the script")
    
    params.pop('action_type', None)
    return main_function(**params)

@validate_arguments
def main(action_id: str, params: Dict[str, Any], swarm_id: SwarmID):
    return action(action_id, params, swarm_id)
