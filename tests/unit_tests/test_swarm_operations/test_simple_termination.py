'''
This operation spawns and terminates a node without running any of the action's blocking methods.
'''
import pytest

from swarmstar.swarm.core import swarmstar_god
from swarmstar.swarm.types import SpawnOperation, NodeEmbryo, SwarmState, TerminationOperation
from tests.utils.get_local_swarm_config import get_swarm_config
from tests.test_config import SWARMSTAR_UNIT_TESTS_MONGODB_DB_NAME

@pytest.mark.unit_test_operations
def test_simple_termination():
    swarm = get_swarm_config(SWARMSTAR_UNIT_TESTS_MONGODB_DB_NAME)
    
    spawn_operation = SpawnOperation(
        operation_type='spawn',
        node_embryo=NodeEmbryo(
            action_id='swarmstar/actions/reasoning/decompose_directive',
            message='Create and add a web browsing action to the swarm\'s action space. The action name should be "browse_web".'
        ),
        termination_policy_change='simple'
    )
    
    first_spawn_output = swarmstar_god(swarm, spawn_operation)[0]
    swarm_state = SwarmState(swarm=swarm)
    first_node_id = first_spawn_output.node_id

    spawn_operation = SpawnOperation(
        operation_type='spawn',
        node_id=first_node_id,
        node_embryo=NodeEmbryo(
            action_id='swarmstar/actions/reasoning/decompose_directive',
            message='Create and add a web browsing action to the swarm\'s action space. The action name should be "browse_web".'
        ),
        termination_policy_change='simple'
    )
    
    second_spawn_output = swarmstar_god(swarm, spawn_operation)[0]
    second_node_id = second_spawn_output.node_id
    
    terminate_operation = TerminationOperation(
        node_id=second_node_id
    )
    
    next_swarm_operation = swarmstar_god(swarm, terminate_operation)[0]
    next_swarm_operation = swarmstar_god(swarm, next_swarm_operation)
    
    try:
        first_node = swarm_state[first_node_id]
        second_node = swarm_state[second_node_id]
        assert first_node.alive == False
        assert second_node.alive == False
    except KeyError:
        pass
