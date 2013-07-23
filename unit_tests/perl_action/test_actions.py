from flow.petri_net import color
from flow_workflow.perl_action import actions
from flow_workflow.parallel_id import ParallelIdentifier
from flow_workflow.historian.operation_data import OperationData

import fakeredis
import mock
import unittest


class PerlActionTest(unittest.TestCase):
    def setUp(self):
        self.action = actions.PerlAction()
        self.args = {
            'method': 'method',
            'action_type': 'action_type',
            'action_id': 'action_id',
            'operation_id': 999,
        }
        self.action.args = self.args

        self.net = mock.Mock()
        self.net.key = 'netkey'

    def test_environment(self):
        operation_id = 42
        color = 9
        color_descriptor = mock.Mock()
        color_descriptor.color = color
        operation_data = OperationData(net_key=self.net.key,
                operation_id=operation_id,
                color=color)

        environment = {
            'foo': 'bar',
            'baz': 'buz',
        }
        self.net.constant.return_value = environment

        result_env = self.action.environment(self.net, color_descriptor)
        self.net.constant.assert_called_once_with('environment', {})

        expected_environment = {
                'FLOW_WORKFLOW_OPERATION_DATA': operation_data.dumps(),
        }
        expected_environment.update(environment)
        self.assertEqual(expected_environment, result_env)

    def test_command_line_no_parallel_index(self):
        expected_value = [
            actions.FLOW_PATH, 'workflow-wrapper',
            '--method', 'method',
            '--action-type', 'action_type',
            '--action-id', 'action_id',
            '--net-key', 'netkey',
            '--operation-id', '999',
        ]

        token_data = {}
        self.assertEqual(expected_value, self.action.command_line(
            self.net, token_data))

    def test_command_line_parallel_index(self):
        expected_value = [
            actions.FLOW_PATH, 'workflow-wrapper',
            '--method', 'method',
            '--action-type', 'action_type',
            '--action-id', 'action_id',
            '--net-key', 'netkey',
            '--operation-id', '999',
            '--parallel-id', '[[3, 4]]',
        ]

        token_data = {'workflow_data': {'parallel_id': [[3, 4]]}}
        self.assertEqual(expected_value, self.action.command_line(
            self.net, token_data))


if __name__ == '__main__':
    unittest.main()
